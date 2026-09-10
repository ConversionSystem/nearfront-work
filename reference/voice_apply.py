#!/usr/bin/env python3
"""Apply a reviewed change set to a page, one exact fragment at a time.

    python3 reference/voice_apply.py <page.html> <changes.md> [--dry-run]

The change set is plain text, so the file that makes the edit is also the
before-and-after record the owner reads:

    ## C1 short label
    optional note lines
    <<<
    the exact fragment as it stands on the page
    ===
    what replaces it
    >>>

Each "before" fragment must occur exactly once in the visible page, with the
head, scripts and styles masked out, or nothing is written. When a change alters
a visible FAQ question or answer, the matching FAQPage string in the JSON-LD is
replaced with the new visible text in the same run, so faq-sync holds without a
hand edit and no other JSON-LD is touched. Exit 0 when every change applied.
"""
import html
import json
import re
import sys

BLOCK_RE = re.compile(r"^## (\S+)[^\n]*\n(?:(?!## |<<<)[^\n]*\n)*?<<<\n(.*?)\n===\n(.*?)\n>>>[ \t]*$", re.S | re.M)
FAQ_RE = re.compile(r'<div class="svc-faq-item"><h3>(.*?)</h3>\s*<p>(.*?)</p>\s*</div>', re.S)
LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def find_all(hay, needle, start=0, end=None):
    end = len(hay) if end is None else end
    out, j = [], hay.find(needle, start, end)
    while j != -1:
        out.append(j)
        j = hay.find(needle, j + 1, end)
    return out


def visible_mask(raw):
    """raw with the head, scripts and styles blanked, the same length so offsets carry over."""
    cut = [(0, max(raw.find("<body"), 0))]
    cut += [(m.start(), m.end()) for m in re.finditer(r"<(script|style)\b.*?</\1>", raw, re.S | re.I)]
    chars = list(raw)
    for s, e in cut:
        chars[s:e] = "\0" * (e - s)
    return "".join(chars)


def plain(fragment):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", fragment)).split())


def mirror(raw, old, new):
    """Swap one FAQPage string, found as a whole JSON string inside the JSON-LD."""
    spans = [(m.start(1), m.end(1)) for m in LD_RE.finditer(raw)]
    for ascii_only in (False, True):
        enc_old = json.dumps(old, ensure_ascii=ascii_only)
        hits = [j for s, e in spans for j in find_all(raw, enc_old, s, e)]
        if len(hits) == 1:
            return raw[:hits[0]] + json.dumps(new, ensure_ascii=ascii_only) + raw[hits[0] + len(enc_old):]
        if len(hits) > 1:
            raise ValueError("appears %d times in the JSON-LD" % len(hits))
    raise ValueError("is not in the JSON-LD")


def main(argv):
    dry = "--dry-run" in argv[1:]
    args = [a for a in argv[1:] if a != "--dry-run"]
    if len(args) != 2:
        print(__doc__)
        return 2
    page, changes = args
    with open(page, encoding="utf-8") as fh:
        raw = fh.read()
    with open(changes, encoding="utf-8") as fh:
        blocks = BLOCK_RE.findall(fh.read())
    if not blocks:
        print("no change blocks in %s" % changes)
        return 2
    out, failed = raw, []
    for cid, old, new in blocks:
        hits = find_all(visible_mask(out), old) if old else []
        if len(hits) != 1:
            failed.append("%s: the before text appears %d times in the visible page" % (cid, len(hits)))
            continue
        out = out[:hits[0]] + new + out[hits[0] + len(old):]
        print("  applied  %s" % cid)
    before, after = FAQ_RE.findall(raw), FAQ_RE.findall(out)
    if len(before) != len(after):
        failed.append("FAQ item count changed %d -> %d; add or remove FAQPage entries by hand"
                      % (len(before), len(after)))
    else:
        for n, ((qb, ab), (qa, aa)) in enumerate(zip(before, after), 1):
            for old, new, part in ((plain(qb), plain(qa), "question"), (plain(ab), plain(aa), "answer")):
                if old == new:
                    continue
                try:
                    out = mirror(out, old, new)
                    print("  mirrored FAQ %d %s into FAQPage" % (n, part))
                except ValueError as err:
                    failed.append("FAQ %d %s: the old text %s" % (n, part, err))
    for f in failed:
        print("  FAILED   " + f)
    if failed:
        print("nothing written")
        return 1
    if dry:
        print("dry run: %d changes would apply to %s" % (len(blocks), page))
        return 0
    with open(page, "w", encoding="utf-8") as fh:
        fh.write(out)
    print("%d changes written to %s" % (len(blocks), page))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
