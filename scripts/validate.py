#!/usr/bin/env python3
"""Nearfront site validator.

Checks the hand-authored static site in public/ against the rules in CLAUDE.md.
Stdlib only, no network, Python 3.9+. Runs in CI, locally, and from Claude Code
or Cowork before a push.

  python3 scripts/validate.py                       whole-tree scan
  python3 scripts/validate.py --base origin/main    only what changed
  python3 scripts/validate.py --check-url /foo/     is this URL free?
  python3 scripts/validate.py --format github       CI annotations
  python3 scripts/validate.py --only redirect-collision
  python3 scripts/validate.py --profile work        sandbox repo rules

Exit: 0 clean (warnings allowed), 1 one or more errors, 2 usage error.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

ERROR, WARN, INFO = "ERROR", "WARN", "INFO"

APEX = "https://nearfront.com"
GTM_ID = "GTM-NFLQTMGP"
NAP_ADDRESS = "550 W B St, 4th Floor, San Diego, CA 92101"
NAP_TEL_HREF = "tel:+17608292735"
LOGIN_URL = "https://app.nearfront.com/login"
CTA_LABEL = "Get Ranked Free"
CTA_HREF = "/book/"

# Pages allowed to name the legal entity in visible copy.
LEGAL_PAGES = {"/privacy-policy/", "/master-subscription-agreement/"}

# One edit to any of these can break every page on the site.
PROTECTED = (
    "public/_redirects", "public/_headers", "public/robots.txt",
    "public/sitemap.xml", "public/index.html", "public/404.html",
    "public/assets/", "public/reports/", "functions/", ".github/", "scripts/",
)

# Reference page for the shared nav/footer shell. Every marketing page must match it.
SHELL_REF = "services/thca-seo/index.html"


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Finding(object):
    def __init__(self, sev, path, line, check, msg, fix=None):
        self.sev, self.path, self.line, self.check = sev, path, line, check
        self.msg, self.fix = msg, fix


class Doc(HTMLParser):
    """Parses one HTML file into the pieces the checks need."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.title = None
        self.metas = {}          # name/property -> (content, line)
        self.canonical = None    # (href, line)
        self.jsonld = []         # (text, line)
        self.links = []          # (href, text, line)
        self.text = []           # (visible text, line)
        self.html_lang = None
        self.has_site_nav = False
        self.has_site_footer = False
        self.nav_hrefs = set()
        self.footer_hrefs = set()
        self.raw = ""
        self._stack = []
        self._grab = None
        self._href = ""
        self._depth = {"nav": 0, "footer": 0}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        line = self.getpos()[0]
        self._stack.append(tag)
        if tag == "html":
            self.html_lang = a.get("lang")
        elif tag == "title":
            self._grab = ("title", line, [])
        elif tag == "meta":
            key = a.get("name") or a.get("property")
            if key and key not in self.metas:
                self.metas[key] = (a.get("content", ""), line)
        elif tag == "link" and a.get("rel") == "canonical":
            self.canonical = (a.get("href", ""), line)
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._grab = ("jsonld", line, [])
        elif tag == "a":
            self._grab = ("a", line, [])
            self._href = a.get("href", "")
        elif tag == "nav":
            if "site-nav" in (a.get("class") or ""):
                self.has_site_nav = True
            self._depth["nav"] += 1
        elif tag == "footer":
            if "site-footer" in (a.get("class") or ""):
                self.has_site_footer = True
            self._depth["footer"] += 1

    def handle_endtag(self, tag):
        if self._stack and tag in self._stack:
            while self._stack and self._stack.pop() != tag:
                pass
        if self._grab and self._grab[0] == tag_kind(tag):
            kind, line, buf = self._grab
            body = "".join(buf)
            if kind == "title":
                self.title = (body.strip(), line)
            elif kind == "jsonld":
                self.jsonld.append((body, line))
            elif kind == "a":
                self.links.append((self._href, body.strip(), line))
                if self._depth["nav"] > 0:
                    self.nav_hrefs.add(self._href)
                if self._depth["footer"] > 0:
                    self.footer_hrefs.add(self._href)
            self._grab = None
        if tag in ("nav", "footer") and self._depth[tag] > 0:
            self._depth[tag] -= 1

    def handle_data(self, data):
        if self._grab:
            self._grab[2].append(data)
        # Visible text only: never script or style bodies.
        if not any(t in ("script", "style") for t in self._stack[-2:]):
            s = data.strip()
            if s:
                self.text.append((s, self.getpos()[0]))


def tag_kind(tag):
    return {"title": "title", "script": "jsonld", "a": "a"}.get(tag, tag)


# --------------------------------------------------------------------------
# _redirects


def parse_redirects(path):
    """-> (exact {source: (line, raw)}, wildcards [(prefix, line, raw)])"""
    exact, wild = {}, []
    if not os.path.exists(path):
        return exact, wild
    with open(path, "r", encoding="utf-8") as fh:
        for n, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            src = parts[0]
            if "*" in src:
                wild.append((src.split("*")[0], n, line))
            else:
                exact[src] = (n, line)
    return exact, wild


def url_for(rel_path):
    """public/services/x/index.html -> /services/x/ ; public/404.html -> /404.html"""
    p = rel_path.replace(os.sep, "/")
    if p.startswith("public/"):
        p = p[len("public/"):]
    if p.endswith("/index.html"):
        p = p[: -len("index.html")]
    elif p == "index.html":
        p = ""
    return "/" + p


def collision(url, exact, wild):
    if url in exact:
        return exact[url]
    bare = url.rstrip("/")
    if bare and bare in exact:
        return exact[bare]
    for prefix, n, raw in wild:
        if prefix and url.startswith(prefix):
            return (n, raw)
    return None


# --------------------------------------------------------------------------
# health claims
#
# Two signals, not one. A bare keyword list fires on "Google treats this
# content..." and gets ignored within a week, which is worse than no check.

TIER_A = re.compile(r"\b(cure[sd]?|curing|treats?|treating|treatment for|heals?|healing|"
                    r"prevents?|prevention of|remedy|therapeutic|medicinal|diagnos[ei]s?|"
                    r"alleviates?|relieves?|relief from|anti-inflammatory|antimicrobial|"
                    r"antiviral|anti-anxiety|antidepressant)\b", re.I)
TIER_B = re.compile(r"\b(cancer|tumors?|epilepsy|seizures?|alzheimer\w*|parkinson\w*|"
                    r"arthritis|chronic pain|insomnia|depression|anxiety disorder|ptsd|"
                    r"diabetes|covid|inflammation|autoimmune|chemotherapy|opioids?|nausea)\b", re.I)
TIER_C = re.compile(r"\b(clinically proven|fda[- ]approved|guaranteed results|100% safe|"
                    r"no side effects|doctor recommended|dosages?|dosing|daily dose|"
                    r"mg per day|for human use|safe for humans|human consumption|"
                    r"weight loss|muscle growth|anti-aging|testosterone boost)\b", re.I)
NEGATED = re.compile(r"\b(no|not|never|without|free of|avoids?|cannot|can't|we do not|"
                     r"is not|research[- ]use|research use only|compliance|compliant|"
                     r"disclaim\w*|prohibit\w*|ban(?:ned|s)?|restrict\w*)\b", re.I)


def health_findings(doc, rel, url):
    out = []
    if url in LEGAL_PAGES:
        return out
    demote = url.startswith("/blog/")
    for chunk, line in doc.text:
        for sentence in re.split(r"(?<=[.!?])\s+", chunk):
            if NEGATED.search(sentence):
                continue
            a, b, c = TIER_A.search(sentence), TIER_B.search(sentence), TIER_C.search(sentence)
            hit, sev = None, None
            if a and b:
                hit, sev = "%s + %s" % (a.group(0), b.group(0)), WARN
            elif c:
                hit, sev = c.group(0), WARN
            elif a:
                hit, sev = a.group(0), INFO
            if not hit:
                continue
            if demote and sev == WARN:
                sev = INFO
            out.append(Finding(sev, rel, line, "health-claim",
                               'possible efficacy claim: "%s" in "%s"' % (hit, sentence[:90]),
                               "These are regulated industries. Use research-use / compliance "
                               "framing, and keep a documented source for every claim."))
    return out


# --------------------------------------------------------------------------


def git_changed(root, base):
    """Committed changes vs base, plus anything uncommitted in the working tree.

    CI diffs commits; a person or an agent running this before a commit has the
    work only in the working tree. Union both so the answer is the same either way.
    """
    found = set()
    ok = False
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", "%s...HEAD" % base],
            cwd=root, stderr=subprocess.STDOUT).decode("utf-8", "replace")
        found.update(x.strip() for x in out.splitlines() if x.strip())
        ok = True
    except Exception:
        pass
    try:
        # -uall lists untracked FILES. Without it git reports a brand-new page as
        # its directory ("public/webinars/"), and the new file is never checked.
        out = subprocess.check_output(
            ["git", "status", "--porcelain", "-uall"],
            cwd=root, stderr=subprocess.STDOUT).decode("utf-8", "replace")
        for line in out.splitlines():
            if len(line) > 3 and not line[:2].strip().startswith("D"):
                found.add(line[3:].strip().split(" -> ")[-1])
        ok = True
    except Exception:
        pass
    return found if ok else None


def html_files(public):
    out = []
    for dirpath, _dirs, files in os.walk(public):
        for f in files:
            if f.endswith(".html"):
                full = os.path.join(dirpath, f)
                out.append(os.path.relpath(full, os.path.dirname(public)).replace(os.sep, "/"))
    return sorted(out)


def profile_for(url, rel, work=False):
    """Which head/brand contract applies to this file.

    marketing - full contract (canonical, OG, JSON-LD, indexable)
    error     - 404 page: reduced contract, noindex is correct
    report    - self-contained page: client dashboards, and on the work host
                the proposals and the host index. No head contract at all.
    """
    if rel.startswith("public/reports/"):
        return "report"
    if work and (rel == "public/index.html" or rel.startswith("public/proposals/")):
        return "report"
    if rel == "public/404.html":
        return "error"
    return "marketing"


def validate(root, args):
    work = args.profile == "work"
    public = os.path.join(root, "public")
    findings = []
    add = findings.append

    changed = git_changed(root, args.base) if args.base else None
    if args.base and changed is None:
        add(Finding(INFO, "-", 0, "git-context",
                    "no git context for --base %s; scanning the whole tree" % args.base))

    redirects_path = os.path.join(public, "_redirects")
    if not os.path.exists(redirects_path):
        alt = os.path.join(root, "reference", "_redirects")
        if os.path.exists(alt):
            redirects_path = alt
    exact, wild = parse_redirects(redirects_path)

    pages = html_files(public)
    docs, urls = {}, {}
    for rel in pages:
        try:
            with open(os.path.join(root, rel), "r", encoding="utf-8") as fh:
                raw = fh.read()
        except Exception as e:
            add(Finding(ERROR, rel, 0, "unreadable", str(e)))
            continue
        d = Doc()
        try:
            d.feed(raw)
        except Exception as e:
            add(Finding(ERROR, rel, 0, "html-parse", "could not parse: %s" % e))
            continue
        d.raw = raw
        docs[rel] = d
        urls[rel] = url_for(rel)

    in_scope = [p for p in pages if changed is None or p in changed]

    # --- flat html ---------------------------------------------------------
    for rel in in_scope:
        base = os.path.basename(rel)
        if base != "index.html" and rel != "public/404.html":
            add(Finding(ERROR, rel, 1, "flat-html",
                        "pages must be public/<path>/index.html for clean URLs",
                        "Move it to %s/index.html. Only public/404.html may be flat."
                        % rel[:-5]))

    # --- redirect collision (the one that fails silently in production) ----
    for rel in in_scope:
        if rel not in docs:
            continue
        hit = collision(urls[rel], exact, wild)
        if hit:
            n, raw = hit
            add(Finding(ERROR, rel, 1, "redirect-collision",
                        "URL %s is already claimed by public/_redirects line %d:\n    %s"
                        % (urls[rel], n, raw),
                        "Cloudflare applies _redirects BEFORE serving files, so this page "
                        "would be unreachable: visitors get 301'd away and Google never "
                        "indexes it. Pick another URL (try --check-url), or retarget that "
                        "rule in this same change."))

    for prefix, n, raw in wild:
        if prefix.startswith("/reports/") and not raw.startswith("/reports/vet-group/"):
            add(Finding(ERROR, "public/_redirects", n, "reports-wildcard-redirect",
                        "wildcard rule under /reports/: %s" % raw,
                        "A /reports/* wildcard shadows the live client dashboards, which are "
                        "real files. Use exact paths only."))

    # --- head contract -----------------------------------------------------
    titles = {}
    for rel in pages:
        d = docs.get(rel)
        if d is None:
            continue
        if profile_for(urls[rel], rel, work) != "report" and d.title and d.title[0]:
            titles.setdefault(d.title[0], []).append(rel)

    for rel in in_scope:
        d = docs.get(rel)
        if d is None:
            continue
        url, prof = urls[rel], profile_for(urls[rel], rel, work)
        if prof == "report":
            robots = d.metas.get("robots")
            if not robots or "noindex" not in robots[0].lower():
                add(Finding(ERROR, rel, robots[1] if robots else 1,
                            "work-noindex-meta" if work else "reports-invariants",
                            "self-contained page is missing noindex"))
            continue  # otherwise exempt: no canonical/OG/JSON-LD by design

        if not d.title or not d.title[0]:
            add(Finding(ERROR, rel, 1, "head-title", "missing or empty <title>"))
        else:
            t, ln = d.title
            if len(titles.get(t, [])) > 1:
                add(Finding(ERROR, rel, ln, "head-title-unique",
                            'title "%s" is also used by %s'
                            % (t, ", ".join(p for p in titles[t] if p != rel)),
                            "Every page needs a distinct title or they compete in search."))
            if not (15 <= len(t) <= 70):
                add(Finding(WARN, rel, ln, "head-title-length",
                            "title is %d chars (aim 15-70)" % len(t)))

        desc = d.metas.get("description")
        if not desc or not desc[0].strip():
            add(Finding(ERROR, rel, 1, "head-description", "missing meta description"))
        elif not (50 <= len(desc[0]) <= 165):
            add(Finding(WARN, rel, desc[1], "head-description-length",
                        "meta description is %d chars (aim 50-165)" % len(desc[0])))

        if not d.canonical:
            add(Finding(ERROR, rel, 1, "head-canonical", "missing <link rel=canonical>"))
        else:
            href, ln = d.canonical
            want = APEX + url
            if href.startswith("http://"):
                add(Finding(ERROR, rel, ln, "head-canonical", "canonical uses http://"))
            elif "://www." in href:
                add(Finding(ERROR, rel, ln, "head-canonical",
                            "canonical uses www; the site canonicalises on the apex"))
            elif prof == "marketing" and not href.endswith("/"):
                add(Finding(ERROR, rel, ln, "head-canonical",
                            "canonical %s is missing its trailing slash" % href))
            elif prof == "marketing" and href != want:
                add(Finding(ERROR, rel, ln, "head-canonical",
                            "canonical is %s but this file serves %s" % (href, want)))

        for key in ("og:type", "og:title", "og:description", "og:url", "og:image"):
            if key not in d.metas:
                add(Finding(ERROR, rel, 1, "head-og", "missing %s" % key))
        og_url = d.metas.get("og:url")
        if og_url and d.canonical and og_url[0] != d.canonical[0]:
            add(Finding(WARN, rel, og_url[1], "head-og-url",
                        "og:url (%s) does not match canonical (%s)" % (og_url[0], d.canonical[0])))

        needed_tw = ("twitter:card",) if prof == "error" else \
                    ("twitter:card", "twitter:title", "twitter:description")
        for key in needed_tw:
            if key not in d.metas:
                add(Finding(ERROR, rel, 1, "head-twitter", "missing %s" % key))

        for body, ln in d.jsonld:
            try:
                json.loads(body)
            except ValueError as e:
                add(Finding(ERROR, rel, ln, "head-jsonld",
                            "JSON-LD does not parse: %s" % e,
                            "Structured data that fails to parse is ignored by Google."))
        if prof == "marketing" and not d.jsonld:
            add(Finding(WARN, rel, 1, "head-jsonld-present", "no JSON-LD block on a marketing page"))

        robots = d.metas.get("robots")
        if work:
            if not robots or "noindex" not in robots[0].lower():
                add(Finding(ERROR, rel, robots[1] if robots else 1, "work-noindex-meta",
                            "every page on the work host needs noindex",
                            'Add <meta name="robots" content="noindex,nofollow">. This host '
                            "must never compete with nearfront.com in search."))
        elif prof == "marketing" and robots and "noindex" in robots[0].lower():
            add(Finding(ERROR, rel, robots[1], "head-robots-index",
                        "marketing page carries noindex: %s" % robots[0],
                        "This silently removes the page from Google. Use index,follow."))

        if d.html_lang is None:
            add(Finding(ERROR, rel, 1, "head-basics", "<html> has no lang attribute"))
        if "viewport" not in d.metas:
            add(Finding(ERROR, rel, 1, "head-basics", "missing viewport meta"))

    # --- GTM ---------------------------------------------------------------
    # Production: every page. Work host: landing pages and drafts only, so
    # campaign conversions are measurable while the host index and the
    # confidential proposals stay out of analytics (same rule as /reports/).
    for rel in in_scope:
        d = docs.get(rel)
        if d is None:
            continue
        if work and profile_for(urls[rel], rel, work) == "report":
            continue
        n = d.raw.count(GTM_ID)
        if n < 2:
            add(Finding(ERROR, rel, 1, "gtm",
                        "expected the GTM head snippet and the noscript iframe (%s appears %d time(s))"
                        % (GTM_ID, n),
                        "Copy both blocks from public/%s." % SHELL_REF))
        for other in set(re.findall(r"GTM-[A-Z0-9]{4,}", d.raw)):
            if other != GTM_ID:
                add(Finding(ERROR, rel, 1, "gtm-foreign",
                            "unexpected container %s; this site uses %s only" % (other, GTM_ID)))

    # --- em dash (HTML only; assets carry them in comments) ----------------
    for rel in in_scope:
        d = docs.get(rel)
        if d is None:
            continue
        for i, line in enumerate(d.raw.splitlines(), 1):
            if re.search(r"\u2014|&mdash;|&#8212;|&#x2014;", line):
                add(Finding(ERROR, rel, i, "em-dash",
                            "em dash in %s" % line.strip()[:80],
                            "House style bans em dashes. Use a comma, a period, parentheses, "
                            "or the middot. En dashes and arrows are fine."))

    # --- legal entity leak -------------------------------------------------
    for rel in in_scope:
        d = docs.get(rel)
        if d is None or urls[rel] in LEGAL_PAGES:
            continue
        for i, line in enumerate(d.raw.splitlines(), 1):
            if "Nubravo" in line and "legalName" not in line:
                add(Finding(ERROR, rel, i, "nubravo-leak",
                            "legal entity named outside a legal page",
                            'Public copy says "Nearfront". Nubravo, LLC belongs only on '
                            "/privacy-policy/ and /master-subscription-agreement/, or as "
                            'JSON-LD "legalName".'))

    # --- health claims -----------------------------------------------------
    for rel in in_scope:
        d = docs.get(rel)
        if d is None or profile_for(urls[rel], rel, work) == "report":
            continue
        findings.extend(health_findings(d, rel, urls[rel]))

    # --- brand + shared shell ---------------------------------------------
    ref = docs.get("public/" + SHELL_REF)
    for rel in in_scope:
        d = docs.get(rel)
        if d is None or profile_for(urls[rel], rel, work) != "marketing":
            continue
        for href, text, ln in d.links:
            if text == CTA_LABEL and href != CTA_HREF:
                add(Finding(ERROR, rel, ln, "brand-cta",
                            '"%s" must link to %s (found %s)' % (CTA_LABEL, CTA_HREF, href)))
            if text == "Log In" and href != LOGIN_URL:
                add(Finding(ERROR, rel, ln, "brand-login",
                            "Log In must point at %s (found %s)" % (LOGIN_URL, href)))
            if href.startswith("tel:") and href != NAP_TEL_HREF:
                add(Finding(ERROR, rel, ln, "brand-nap-phone",
                            "tel: link is %s; the NAP number is %s" % (href, NAP_TEL_HREF),
                            "Inconsistent tel: hrefs break GTM click tracking and NAP consistency."))
        # The address is routinely split across tags and lines, so compare against
        # a tag-stripped, whitespace-collapsed view rather than raw lines.
        flat = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", d.raw))
        for m in re.finditer(r"W\s+B\s+St", flat):
            window = flat[max(0, m.start() - 40):m.end() + 90]
            zips = set(re.findall(r"\b\d{5}\b", window))
            if ("550 W B St" not in window or "4th Floor" not in window
                    or "San Diego" not in window or (zips and zips != {"92101"})):
                add(Finding(ERROR, rel, 1, "brand-nap-address",
                            "address differs from the NAP: %s" % window.strip()[:100],
                            "NAP must read exactly: %s" % NAP_ADDRESS))
        for i, line in enumerate(d.raw.splitlines(), 1):
            if "http://nearfront.com" in line or "https://www.nearfront.com" in line:
                add(Finding(ERROR, rel, i, "brand-domain",
                            "use https://nearfront.com (apex, https)"))
        if not d.has_site_nav:
            add(Finding(ERROR, rel, 1, "brand-shell", 'missing <nav class="site-nav">'))
        if not d.has_site_footer:
            add(Finding(ERROR, rel, 1, "brand-shell", 'missing <footer class="site-footer">'))
        if ref is not None and rel != "public/" + SHELL_REF:
            for label, got, want in (("nav", d.nav_hrefs, ref.nav_hrefs),
                                     ("footer", d.footer_hrefs, ref.footer_hrefs)):
                if got and want and got != want:
                    missing, extra = sorted(want - got), sorted(got - want)
                    bits = []
                    if missing:
                        bits.append("missing %s" % ", ".join(missing))
                    if extra:
                        bits.append("extra %s" % ", ".join(extra))
                    add(Finding(ERROR, rel, 1, "brand-shell",
                                "%s links differ from public/%s: %s"
                                % (label, SHELL_REF, "; ".join(bits)),
                                "The nav and footer are copied verbatim into every page. "
                                "Changing one page's set is almost always a mistake."))

    # --- internal links (production only: work drafts link to production URLs)
    for rel in (in_scope if not work else []):
        d = docs.get(rel)
        if d is None:
            continue
        for href, _text, ln in d.links:
            if not href.startswith("/") or href.startswith("//"):
                continue
            target = href.split("#")[0].split("?")[0]
            if not target or target == "/":
                continue
            fs = os.path.join(public, target.strip("/").replace("/", os.sep))
            ok = os.path.isfile(fs) or os.path.isfile(os.path.join(fs, "index.html"))
            if not ok and collision(target if target.endswith("/") else target + "/",
                                    exact, wild) is None \
                    and collision(target, exact, wild) is None:
                add(Finding(ERROR, rel, ln, "internal-link",
                            "link to %s does not resolve to a page, an asset, or a redirect" % href))

    # --- dead redirect targets --------------------------------------------
    if not work and (changed is None or "public/_redirects" in changed):
        for src, (n, raw) in exact.items():
            parts = raw.split()
            if len(parts) < 2:
                continue
            dest = parts[1]
            if not dest.startswith("/") or dest.startswith("//"):
                continue
            d0 = dest.split("#")[0].split("?")[0]
            if d0 == "/":
                continue
            fs = os.path.join(public, d0.strip("/").replace("/", os.sep))
            if not (os.path.isfile(fs) or os.path.isfile(os.path.join(fs, "index.html"))):
                add(Finding(ERROR, "public/_redirects", n, "redirect-target-dead",
                            "redirect target %s does not exist" % dest))

    # --- client dashboard invariants --------------------------------------
    for rel in pages:
        if not rel.startswith("public/reports/"):
            continue
        d = docs.get(rel)
        if d is None:
            continue
        robots = d.metas.get("robots", ("", 1))
        if "noindex" not in robots[0].lower():
            add(Finding(ERROR, rel, robots[1], "reports-invariants",
                        "client dashboard is missing noindex",
                        "These pages are confidential client work."))
    headers_path = os.path.join(public, "_headers")
    if os.path.exists(headers_path):
        htxt = open(headers_path, "r", encoding="utf-8").read()
        if args.profile != "work":
            if "/reports/*" not in htxt or "noindex" not in htxt.split("/reports/*")[-1][:200]:
                add(Finding(ERROR, "public/_headers", 1, "reports-invariants",
                            "the /reports/* X-Robots-Tag noindex block is missing or altered",
                            "Without it the client dashboards become indexable."))
        elif "X-Robots-Tag" not in htxt or "noindex" not in htxt:
            add(Finding(ERROR, "public/_headers", 1, "work-noindex",
                        "this host must serve X-Robots-Tag: noindex on /*"))

    # --- robots.txt --------------------------------------------------------
    robots_path = os.path.join(public, "robots.txt")
    if os.path.exists(robots_path):
        lines = open(robots_path, "r", encoding="utf-8").read().splitlines()
        for i, line in enumerate(lines, 1):
            if re.match(r"^\s*Disallow:\s*/\s*$", line):
                add(Finding(ERROR, "public/robots.txt", i, "robots-disallow-all",
                            '"Disallow: /" blocks the whole site',
                            "This does NOT deindex. It stops Google fetching pages, so Google "
                            "never reads your noindex, and URLs found via links get indexed "
                            "URL-only. To deindex, ALLOW crawling and serve X-Robots-Tag: "
                            "noindex from _headers."))
        has_sitemap = any(l.strip().lower().startswith("sitemap:") for l in lines)
        if args.profile == "work" and has_sitemap:
            add(Finding(ERROR, "public/robots.txt", 1, "work-no-sitemap",
                        "the work host must not advertise a sitemap"))
        elif args.profile != "work" and not has_sitemap:
            add(Finding(ERROR, "public/robots.txt", 1, "robots-sitemap",
                        "robots.txt should point at %s/sitemap.xml" % APEX))

    # --- sitemap -----------------------------------------------------------
    sm_path = os.path.join(public, "sitemap.xml")
    if args.profile != "work" and os.path.exists(sm_path):
        try:
            tree = ET.parse(sm_path)
            ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
            locs = [e.text.strip() for e in tree.getroot().iter(ns + "loc") if e.text]
            seen = set()
            for loc in locs:
                if loc in seen:
                    add(Finding(ERROR, "public/sitemap.xml", 1, "sitemap",
                                "duplicate <loc> %s" % loc))
                seen.add(loc)
                if "/reports/" in loc:
                    add(Finding(ERROR, "public/sitemap.xml", 1, "sitemap",
                                "confidential dashboard listed in the sitemap: %s" % loc))
                if not loc.startswith(APEX + "/"):
                    add(Finding(ERROR, "public/sitemap.xml", 1, "sitemap",
                                "<loc> is not on the apex: %s" % loc))
                    continue
                path = loc[len(APEX):]
                fs = os.path.join(public, path.strip("/").replace("/", os.sep))
                if not (os.path.isfile(fs) or os.path.isfile(os.path.join(fs, "index.html"))):
                    add(Finding(ERROR, "public/sitemap.xml", 1, "sitemap",
                                "<loc> %s has no matching page" % loc))
            if changed:
                for rel in in_scope:
                    if profile_for(urls[rel], rel, work) != "marketing" or rel not in changed:
                        continue
                    if APEX + urls[rel] in seen:
                        continue
                    is_new = True
                    try:
                        subprocess.check_output(
                            ["git", "cat-file", "-e", "%s:%s" % (args.base, rel)],
                            cwd=root, stderr=subprocess.STDOUT)
                        is_new = False
                    except Exception:
                        pass
                    if is_new:
                        add(Finding(ERROR, "public/sitemap.xml", 1, "sitemap-missing-page",
                                    "new page %s is not in the sitemap" % urls[rel],
                                    "Add a <url> entry so Google can discover it."))
        except ET.ParseError as e:
            add(Finding(ERROR, "public/sitemap.xml", 1, "sitemap",
                        "sitemap is not well-formed XML: %s" % e,
                        "Search Console rejects the whole file, not just the bad line."))

    # --- asset versioning --------------------------------------------------
    versions = {"css": {}, "js": {}}
    for rel in pages:
        d = docs.get(rel)
        if d is None or profile_for(urls[rel], rel, work) == "report":
            continue
        for kind, pat in (("css", r"site\.css\?v=(\d+)"), ("js", r"site\.js\?v=(\d+)")):
            m = re.search(pat, d.raw)
            if m:
                versions[kind].setdefault(m.group(1), []).append(rel)
    for kind, seen in versions.items():
        if len(seen) > 1:
            worst = sorted(seen.items(), key=lambda kv: -len(kv[1]))
            detail = "; ".join("v=%s on %d page(s)" % (v, len(ps)) for v, ps in worst)
            for v, ps in worst[1:]:
                for rel in ps:
                    add(Finding(ERROR, rel, 1, "asset-version-uniform",
                                "site.%s is at v=%s but most pages use v=%s (%s)"
                                % (kind, v, worst[0][0], detail),
                                "All pages must request the same asset version."))
    if changed:
        for kind, asset in (("css", "public/assets/site.css"), ("js", "public/assets/site.js")):
            if asset not in changed:
                continue
            cur = sorted(versions[kind].keys())
            try:
                old = subprocess.check_output(
                    ["git", "show", "%s:public/%s" % (args.base, SHELL_REF)],
                    cwd=root, stderr=subprocess.STDOUT).decode("utf-8", "replace")
                om = re.search(r"site\.%s\?v=(\d+)" % kind, old)
                if om and cur and int(cur[0]) <= int(om.group(1)):
                    add(Finding(ERROR, asset, 1, "asset-version-bump",
                                "%s changed but pages still request v=%s" % (asset, cur[0]),
                                "_headers caches /assets/* for a year with immutable, so "
                                "returning visitors will never see this change. Bump ?v=N "
                                "on every page that links it."))
            except Exception:
                add(Finding(WARN, asset, 1, "asset-version-bump",
                            "%s changed; could not confirm the ?v=N bump without git" % asset))

    # --- legacy element selectors -----------------------------------------
    css_path = os.path.join(public, "assets", "site.css")
    if os.path.exists(css_path):
        css = re.sub(r"/\*.*?\*/", "", open(css_path, "r", encoding="utf-8").read(), flags=re.S)
        for block in css.split("}"):
            if "{" not in block:
                continue
            for token in block.rsplit("{", 1)[0].split(","):
                if token.strip() in ("nav", "footer"):
                    add(Finding(ERROR, "public/assets/site.css", 1, "legacy-element-selector",
                                'bare "%s {" selector' % token.strip(),
                                "It matches .site-footer's markup and pins the footer to the "
                                "top of every page. Scope it to .site-nav / .site-footer."))

    # --- committed secrets -------------------------------------------------
    secret_pats = [
        (r"CLOUDFLARE_API_TOKEN\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}", "Cloudflare token"),
        (r"RESEND_API_KEY\s*[:=]\s*['\"]?re_[A-Za-z0-9_\-]{10,}", "Resend key"),
        (r"re_[A-Za-z0-9]{8,}_[A-Za-z0-9]{20,}", "Resend key"),
        (r"-----BEGIN [A-Z ]*PRIVATE KEY", "private key"),
        (r"\bghp_[A-Za-z0-9]{36}\b", "GitHub token"),
        (r"\bsk-[A-Za-z0-9]{20,}\b", "API key"),
    ]
    for rel in (in_scope if changed is not None else pages):
        d = docs.get(rel)
        if d is None:
            continue
        for pat, what in secret_pats:
            m = re.search(pat, d.raw)
            if m:
                ln = d.raw[:m.start()].count("\n") + 1
                add(Finding(ERROR, rel, ln, "secrets-scan",
                            "looks like a committed %s" % what,
                            "Secrets belong in Cloudflare Pages project settings, never in git."))

    # --- page weight (dashboards are data-heavy by design) -----------------
    for rel in in_scope:
        d = docs.get(rel)
        if d is None or profile_for(urls[rel], rel, work) == "report":
            continue
        kb = len(d.raw.encode("utf-8")) / 1024.0
        if kb > 250:
            add(Finding(WARN, rel, 1, "page-weight", "page is %.0f KB" % kb,
                        "Large pages hurt Core Web Vitals. Check for inlined base64 images."))

    # --- protected paths banner -------------------------------------------
    if changed:
        touched = sorted(p for p in changed if p.startswith(PROTECTED))
        if touched:
            add(Finding(WARN, "-", 0, "protected-paths",
                        "this change touches site-wide files:\n    " + "\n    ".join(touched),
                        "One bad edit here affects every page. A human who knows the site "
                        "should read these hunks line by line before merge."))

    return findings


def check_url(root, url):
    public = os.path.join(root, "public")
    path = os.path.join(public, "_redirects")
    if not os.path.exists(path):
        path = os.path.join(root, "reference", "_redirects")
    exact, wild = parse_redirects(path)
    if not url.startswith("/"):
        url = "/" + url
    if not url.endswith("/"):
        url += "/"
    hit = collision(url, exact, wild)
    fs = os.path.join(public, url.strip("/").replace("/", os.sep), "index.html")
    if hit:
        print("CLAIMED  %s\n  %s:%d  %s" % (url, os.path.relpath(path, root), hit[0], hit[1]))
        print("  A page here would be unreachable: Cloudflare applies the redirect first.")
        print("  Pick another URL. Nesting under /services/ or /blog/ almost always works.")
        return 1
    if os.path.isfile(fs):
        print("TAKEN    %s already exists at %s" % (url, os.path.relpath(fs, root)))
        return 1
    print("FREE     %s is available." % url)
    return 0


def report(findings, fmt):
    order = {ERROR: 0, WARN: 1, INFO: 2}
    findings.sort(key=lambda f: (order[f.sev], f.path, f.line))
    errors = sum(1 for f in findings if f.sev == ERROR)
    warns = sum(1 for f in findings if f.sev == WARN)
    infos = len(findings) - errors - warns

    if fmt == "github":
        for f in findings:
            lvl = {ERROR: "error", WARN: "warning", INFO: "notice"}[f.sev]
            msg = f.msg.replace("\n", "%0A")
            if f.fix:
                msg += "%0AFix: " + f.fix.replace("\n", " ")
            loc = ""
            if f.path != "-":
                loc = "file=%s," % f.path + ("line=%d," % f.line if f.line else "")
            print("::%s %stitle=%s::%s" % (lvl, loc, f.check, msg))
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as fh:
                fh.write("## Site validation\n\n")
                fh.write("**%d errors, %d warnings, %d notices**\n\n" % (errors, warns, infos))
                if findings:
                    fh.write("| | check | where | what |\n|---|---|---|---|\n")
                    for f in findings:
                        icon = {ERROR: "x", WARN: "!", INFO: "i"}[f.sev]
                        where = f.path if f.path != "-" else "(change)"
                        if f.line:
                            where += ":%d" % f.line
                        one = f.msg.split("\n")[0].replace("|", "\\|")
                        fh.write("| %s | `%s` | `%s` | %s |\n" % (icon, f.check, where, one))
    else:
        mark = {ERROR: "x ERROR", WARN: "! WARN ", INFO: "i INFO "}
        for f in findings:
            where = f.path if f.path != "-" else "(change)"
            if f.line:
                where += ":%d" % f.line
            print("  %s  %s  [%s]" % (mark[f.sev], where, f.check))
            for ln in f.msg.split("\n"):
                print("          %s" % ln)
            if f.fix:
                print("          Fix: %s" % f.fix)
            print("")
        print("%d errors, %d warnings, %d notices - %s"
              % (errors, warns, infos, "FAILED" if errors else "OK"))
    return errors


def main():
    ap = argparse.ArgumentParser(description="Validate the Nearfront static site.")
    ap.add_argument("--base", help="git ref to diff against (e.g. origin/main)")
    ap.add_argument("--format", choices=["text", "github"], default="text")
    ap.add_argument("--profile", choices=["site", "work"], default="site")
    ap.add_argument("--only", help="comma-separated check ids")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--check-url", help="ask whether a URL is free, then exit")
    args = ap.parse_args()

    root = repo_root()
    if args.check_url:
        return check_url(root, args.check_url)

    findings = validate(root, args)
    if args.only:
        keep = set(x.strip() for x in args.only.split(","))
        findings = [f for f in findings if f.check in keep]
    if args.strict:
        for f in findings:
            if f.sev == WARN:
                f.sev = ERROR

    if args.format == "text":
        n_pages = len(html_files(os.path.join(root, "public")))
        mode = "diff vs %s" % args.base if args.base else "whole tree"
        print("\nnearfront validate - %d pages, %s\n" % (n_pages, mode))

    return 1 if report(findings, args.format) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(2)
