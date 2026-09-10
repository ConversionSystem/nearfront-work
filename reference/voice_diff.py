#!/usr/bin/env python3
"""Block a voice rewrite that changes a page's facts.

The human-voice pass (plan Workstream D) rewrites prose. It must never change a
number, a date, a URL, a quotation or a source name, and it never edits JSON-LD.
This makes that mechanical instead of a matter of care.

    python3 reference/voice_diff.py compare <before.html> <after.html>
    python3 reference/voice_diff.py snapshot <page.html> <snapshot.json>
    python3 reference/voice_diff.py check <snapshot.json> <page.html>

A fact that was on the page and is gone is BLOCKED. A fact that is new is ADDED,
also a failure, because the pass never adds a metric. A fact that appears fewer
times is only noted: cutting a restatement is the point of the pass. JSON-LD
outside FAQPage must be identical. FAQ answer edits are counted so the FAQPage
mirror step is not forgotten. Exit 0 on PASS, 1 otherwise.
"""
import html
import json
import re
import sys
from collections import Counter

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
# Thousands groups must be exactly three digits, so "2026," does not swallow its comma and a
# rewrite that only changes the punctuation after a number is not mistaken for a lost fact.
NUM_RE = re.compile(r"\$?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:\s?(?:%|percent\b|million\b|billion\b|[MBK]\b))?")
WORDNUM_RE = re.compile(r"\b(two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
                        r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|"
                        r"seventy|eighty|ninety|hundred|thousand)\b", re.I)
DATE_RE = re.compile(r"\b(?:\d{1,2} )?(?:%s)(?: \d{1,2},?)? \d{4}\b|\bFY ?\d{4}\b|\b\d{4}-\d{2}-\d{2}\b" % MONTHS)
QUOTE_RE = re.compile(r'"([^"]{8,400}?)"|“([^”]{8,400}?)”')
SOURCE_RE = re.compile(r"\b(?:[A-Z][A-Za-z&.'-]+ ){0,6}(?:Board|Department|Office|Administration|Commission|"
                       r"Division|Agency|Bureau|Authority|Treasury|Registry|Council|Management)\b"
                       r"(?: (?:of|for|and) (?:[A-Z][A-Za-z&.'-]+ ?){1,5})?")
# A capitalized word that only opens the sentence is not part of the name. "The Michigan Treasury",
# "Michigan's Treasury" and "On Treasury's count" all name the Treasury, so rewording a sentence
# around a source must not read as losing it.
SOURCE_LEAD = re.compile(r"^(?:(?:The|A|An|And|But|Or|So|On|In|At|By|For|From|Of|To|With|Per|Once|When|While|"
                         r"If|As|Since|After|Before|Every|Each|That|This|These|Those|Its|Their|Our|Your|"
                         r"Then|Also|Only|Both|Statewide) )+")


def source_key(name):
    return SOURCE_LEAD.sub("", re.sub(r"'s\b", "", " ".join(name.split())))


def body(raw):
    b = raw.split("</head>", 1)[-1]
    return re.sub(r"<(script|style|nav|footer)\b.*?</\1>", " ", b, flags=re.S | re.I)


def text(fragment):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def facts(raw):
    b = body(raw)
    t = text(b)
    return {
        "number": Counter(" ".join(m.split()) for m in NUM_RE.findall(t)),
        "number-word": Counter(m.lower() for m in WORDNUM_RE.findall(t)),
        "date": Counter(DATE_RE.findall(t)),
        "quote": Counter((a or c).strip() for a, c in QUOTE_RE.findall(t)),
        "url": Counter(re.findall(r'href="([^"]+)"', b)),
        "source": Counter(source_key(m) for m in SOURCE_RE.findall(t)),
    }


def jsonld_outside_faq(raw):
    out = []
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', raw, re.S):
        try:
            d = json.loads(m.group(1))
        except Exception:
            out.append("unparseable:" + m.group(1))
            continue
        nodes = d.get("@graph", [d]) if isinstance(d, dict) else d
        out.append(json.dumps([n for n in nodes if not (isinstance(n, dict) and n.get("@type") == "FAQPage")],
                              sort_keys=True))
    return out


def faq(raw):
    return re.findall(r'<div class="svc-faq-item"><h3>(.*?)</h3>\s*<p>(.*?)</p>\s*</div>', raw, re.S)


def voice(raw):
    b = body(raw)
    t = text(b)
    h2 = [text(x) for x in re.findall(r"<h2[^>]*>(.*?)</h2>", b, re.S)]
    # Counted the way the 2026-09-10 baseline in content/brand-voice.md was: sentences of three or
    # more words across the paragraphs, four in a row within six words of each other, then skip four.
    paras = " ".join(text(p) for p in re.findall(r"<p(?:\s[^>]*)?>(.*?)</p>", b, re.S))
    lens = [len(s.split()) for s in re.split(r"(?<=[.!?])\s+", paras) if len(s.split()) >= 3]
    runs, i = 0, 0
    while i <= len(lens) - 4:
        if max(lens[i:i + 4]) - min(lens[i:i + 4]) <= 6:
            runs, i = runs + 1, i + 4
        else:
            i += 1
    return {"In short": t.count("In short:"),
            "question H2s": "%d/%d" % (sum(x.endswith("?") for x in h2), len(h2)),
            "this page/guide": len(re.findall(r"\bthis (?:page|guide)\b", t, re.I)),
            "same-length runs": runs}


def compare(before, after):
    fb, fa = facts(before), facts(after)
    blocked, added, fewer = [], [], []
    for kind in fb:
        for k, n in sorted(fb[kind].items()):
            m = fa[kind].get(k, 0)
            if m == 0:
                blocked.append((kind, k))
            elif m < n:
                fewer.append((kind, k, n, m))
        added += [(kind, k) for k in sorted(fa[kind]) if k not in fb[kind]]
    ld_same = jsonld_outside_faq(before) == jsonld_outside_faq(after)
    qa_b, qa_a = faq(before), faq(after)
    faq_edits = sum(1 for x, y in zip(qa_b, qa_a) if x != y) + abs(len(qa_b) - len(qa_a))
    return {"blocked": blocked, "added": added, "fewer": fewer, "jsonld_same": ld_same,
            "faq_edits": faq_edits, "voice_before": voice(before), "voice_after": voice(after)}


def report(r, label):
    short = lambda s: s if len(s) <= 90 else s[:87] + "..."
    print("voice_diff: %s" % label)
    for kind, k in r["blocked"]:
        print("  BLOCK  %-11s %s was on the page and is gone" % (kind, short(repr(k))))
    for kind, k in r["added"]:
        print("  ADDED  %-11s %s is new" % (kind, short(repr(k))))
    for kind, k, n, m in r["fewer"]:
        print("  note   %-11s %s appears %d -> %d times" % (kind, short(repr(k)), n, m))
    print("  JSON-LD outside FAQPage: %s" % ("identical" if r["jsonld_same"] else "CHANGED"))
    if r["faq_edits"]:
        print("  FAQ answers edited: %d. Mirror them into FAQPage, then run the validator's faq-sync."
              % r["faq_edits"])
    vb, va = r["voice_before"], r["voice_after"]
    print("  voice: " + ", ".join("%s %s -> %s" % (k, vb[k], va[k]) for k in vb))
    ok = not r["blocked"] and not r["added"] and r["jsonld_same"]
    print("RESULT: %s" % ("PASS" if ok else "BLOCKED (%d gone, %d new%s)"
                          % (len(r["blocked"]), len(r["added"]), "" if r["jsonld_same"] else ", JSON-LD changed")))
    return 0 if ok else 1


def read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def main(argv):
    if len(argv) == 4 and argv[1] == "compare":
        return report(compare(read(argv[2]), read(argv[3])), "%s -> %s" % (argv[2], argv[3]))
    if len(argv) == 4 and argv[1] == "snapshot":
        with open(argv[3], "w", encoding="utf-8") as fh:
            json.dump({"page": argv[2], "raw": read(argv[2])}, fh)
        print("snapshot of %s written to %s" % (argv[2], argv[3]))
        return 0
    if len(argv) == 4 and argv[1] == "check":
        snap = json.loads(read(argv[2]))
        return report(compare(snap["raw"], read(argv[3])), "snapshot of %s -> %s" % (snap["page"], argv[3]))
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
