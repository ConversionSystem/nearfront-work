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
from html import unescape as html_unescape
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
# The primary CTA sends people to the funnel, which captures the lead before
# offering the calendar. /book/ stays live for direct booking links.
CTA_HREF = "/get-started/"

# Pages allowed to name the legal entity in visible copy.
LEGAL_PAGES = {"/privacy-policy/", "/master-subscription-agreement/"}

# One edit to any of these can break every page on the site.
PROTECTED = (
    "public/_redirects", "public/_headers", "public/robots.txt",
    "public/sitemap.xml", "public/index.html", "public/404.html",
    "public/assets/", "public/reports/", "functions/", ".github/", "scripts/",
)

# Reference page for the shared nav/footer shell. Every marketing page must match it.
SHELL_REF = "services/cannabis-dispensary-seo/index.html"
# Work-lane stand-ins for SHELL_REF, which only exists in the production repo.
SHELL_FALLBACKS = ("templates/landing-page.html",)

# US agency writing for US businesses. British forms keep creeping into drafts and
# read as foreign on a local-SEO page, which is exactly the wrong signal. Matched
# case-insensitively on word stems, so "licence/licences/licencing" all trip.
BRITISH_SPELLINGS = [
    (r"licenc\w*", "licens-"), (r"neighbour\w*", "neighbor-"), (r"\bcentre", "center"),
    (r"colour\w*", "color-"), (r"organis(?:e|ed|ing|ation)\w*", "organiz-"),
    (r"recognis(?:e|ed|ing)\w*", "recogniz-"),
    # "analyses" is the US plural of "analysis", so only the verb forms are British.
    (r"\banalyse\b|analysed|analysing", "analyze/analyzed/analyzing"),
    (r"programme\w*", "program-"), (r"(?<!aria-)labelled|labelling", "labeled/labeling"),
    (r"categoris(?:e|ed|ing|ation)\w*", "categoriz-"), (r"behaviour\w*", "behavior-"),
    (r"favour(?:s|ed|ing|able)?\b", "favor-"), (r"\bdefence\b", "defense"),
    (r"travelling|travelled", "traveling/traveled"),
]

# Programmatic page families. Pages sharing a prefix are near-siblings by
# construction, so they are the ones at risk of becoming templated duplicates.
# Compared only within their own group; a state page and a city page are
# expected to differ anyway.
GEO_PREFIXES = ("cannabis-seo-", "thca-seo-", "dispensary-near-")

GEO_EXCLUDE = ("cannabis-seo-agency",)
GEO_DEMO_PAGES = {"/dispensary-near-gresham/"}   # a labelled demo; exempt from geo-freshness
MONTH = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
RETRIEVED_RE = re.compile(r"\b(?:read|retrieved|queried|downloaded|checked|pulled|parsed|refreshed)\b[^.;]{0,60}?\b\d{1,2} " + MONTH + r" \d{4}", re.I)
SOURCE_DATE_RE = re.compile(r"\b(?:dated|as of|covering|through|updated|last modified|last edited|stated as of|as published on)\b[^.;]{0,60}?" + MONTH + r" \d{4}", re.I)
# Words that read as machine-written. Advisory; the statutory "comprehensive license" is allowed.
AI_TELLS = [r"\bleverag\w*", r"\bnavigat(?:e|ing) the\b", r"\bunlock\w*", r"\bdelv\w*", r"\bin today'?s\b", r"\bever-evolving\b",
    r"\blandscape\b", r"\bit'?s (?:important|worth) (?:to note|noting)\b", r"\bseamless\w*", r"\brobust\b", r"\bcutting-edge\b",
    r"\bgame-?changer\b", r"\belevat\w*", r"\bempower\w*", r"\bharness\w*", r"\bstreamlin\w*", r"\btapestry\b", r"\btestament to\b",
    r"\bunderscor\w*", r"\bcrucial\b", r"\bpivotal\b", r"\bcomprehensive (?:guide|approach|solution|strategy|overview|look|review|analysis|list|resource|suite|platform|service|support|coverage)s?\b", r"\bholistic\b", r"\bsynerg\w*", r"\bfoster\w*",
    r"\butiliz\w*", r"\bmoreover\b", r"\bfurthermore\b", r"\bin conclusion\b", r"\bdeep dive\b", r"\bdive into\b", r"\bunleash\w*",
    r"\bsupercharge\w*", r"\bskyrocket\w*", r"\bnext level\b", r"\bbest-in-class\b", r"\bworld-class\b", r"\bstate-of-the-art\b",
    r"\brevolutioniz\w*", r"\btransformativ\w*", r"\bmeticulous\w*", r"\bvibrant\b", r"\bbustling\b", r"\bnestled\b", r"\bboast\w*",
    r"\bplethora\b", r"\bmyriad\b", r"\brealm\b", r"\bparamount\b", r"\bembark\w*", r"\bthe world of\b", r"\bbeacon\b"]
# Hub and service pages that must carry a visible FAQ plus FAQPage. Flip HUB_FAQ_ENABLED in the
# same commit that ships those FAQs (plan workstream C1) so the check never nags about planned work.
HUB_FAQ_ENABLED = True
HUB_FAQ_PAGES = {"/services/", "/markets/", "/about-us/", "/vs/", "/how-we-rank-ourselves/", "/get-started/", "/book/", "/seo-rockstars-podcast/"}
# Extra evidence-bearing pages beyond /vs/<name>/ and Article pages; add /vs/ and
# /how-we-rank-ourselves/ when their rebuilds (plan C2) give them sources to link.
EVIDENCE_PAGES = set()
COUNT_DRIFT_FILES = ("public/index.html", "public/services/index.html", "public/markets/index.html", "public/llms.txt", "public/llms-full.txt")

# Directories outside public/ that may legitimately hold .html: page templates,
# archived competitor evidence, and the read-only production reference copies.
NON_SERVED_HTML_DIRS = ("templates/", "content/", "reference/")

# 8-gram Jaccard overlap between two sibling pages, after the shared shell is
# subtracted. Deeproots' suburb pages measure 27-43% duplicate; Bud Authority's
# geo pages run 3-12%. Sitting under 10% keeps us on the right side of that gap.
SHINGLE_WARN = 0.10
SHINGLE_ERROR = 0.15

# Tags that must never be pasted into a page: they belong inside the GTM
# container. A hard-coded tag alongside the container's own double-counts every
# hit, and it dodges the rule that a new tracker ships with its privacy
# disclosure. The vendor "install our pixel" instructions all produce these.
TRACKERS_OUTSIDE_GTM = [
    (r"googletagmanager\.com/gtag/js", "a raw gtag.js tag (GA4 or Google Ads)"),
    (r"google-analytics\.com/(analytics|ga)\.js", "a legacy Google Analytics tag"),
    (r"connect\.facebook\.net|\bfbq\s*\(", "a Meta pixel"),
    (r"static\.ads-twitter\.com|\btwq\s*\(", "an X/Twitter pixel"),
    (r"snap\.licdn\.com|\b_linkedin_partner_id\b", "a LinkedIn insight tag"),
    (r"analytics\.tiktok\.com|\bttq\s*\.", "a TikTok pixel"),
    (r"clarity\.ms", "a Microsoft Clarity tag"),
    (r"static\.hotjar\.com|\bhj\s*\(", "a Hotjar tag"),
    (r"cdn\.segment\.com", "a Segment tag"),
    (r"js\.hs-scripts\.com", "a HubSpot tag"),
    (r"cdn\.callrail\.com|\bcalltrk\b", "a CallRail tag"),
]


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
        # Count nav/footer nesting so link capture can be scoped to the BRANDED
        # shell only. The footer contains <nav class="footer-links">, so a plain
        # "am I inside any <nav>" test folds every footer link into nav_hrefs and
        # makes the shell comparison nearly a no-op.
        self._nav_open = self._footer_open = 0
        self._site_nav_at = self._site_footer_at = None

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
            self._nav_open += 1
            if "site-nav" in (a.get("class") or ""):
                self.has_site_nav = True
                if self._site_nav_at is None:
                    self._site_nav_at = self._nav_open
        elif tag == "footer":
            self._footer_open += 1
            if "site-footer" in (a.get("class") or ""):
                self.has_site_footer = True
                if self._site_footer_at is None:
                    self._site_footer_at = self._footer_open

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
                if self._site_nav_at is not None:
                    self.nav_hrefs.add(self._href)
                if self._site_footer_at is not None:
                    self.footer_hrefs.add(self._href)
            self._grab = None
        if tag == "nav" and self._nav_open > 0:
            if self._site_nav_at == self._nav_open:
                self._site_nav_at = None
            self._nav_open -= 1
        elif tag == "footer" and self._footer_open > 0:
            if self._site_footer_at == self._footer_open:
                self._site_footer_at = None
            self._footer_open -= 1

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


def shingles(raw, n=8):
    """Set of n-word shingles over a page's visible text.

    Scripts and styles are dropped first: JSON-LD mirrors the visible FAQ by
    design, and counting it would make every well-marked-up page look like a
    duplicate of itself.
    """
    txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S | re.I)
    words = re.findall(r"[a-z0-9]+", re.sub(r"<[^>]+>", " ", txt).lower())
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


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
# "treat X as Y" is a rhetorical construction, never a medical claim. On
# 2026-08-12 it accounted for every single health-claim notice on the site, 13
# of 13, which is precisely the "ignored within a week" failure the tiering
# above was built to avoid. Suppressed only when the sentence carries no
# condition term, so "treat chronic pain as needed" still fires.
TREAT_AS = re.compile(r"\btreat(?:s|ed|ing)?\b(?:\s+\S+){0,10}?\s+\bas\b", re.I)

# "intended for human consumption" is the scope language of state hemp food
# rules (Florida 5K-4.034 and its equivalents), so a page that quotes the rule
# it must comply with trips TIER_C on the phrase "human consumption". Stripped
# before the TIER_C probe on hemp and cannabis pages only. It is NEVER stripped
# under /peptides/, where research-use framing is the whole point and any
# "for human consumption" wording must still fire.
REG_SCOPE = re.compile(r"\bintended for human consumption\b", re.I)

NEGATED = re.compile(r"\b(no|not|never|without|free of|avoids?|cannot|can't|we do not|"
                     r"is not|research[- ]use|research use only|compliance|compliant|"
                     r"disclaim\w*|prohibit\w*|ban(?:ned|s)?|restrict\w*)\b", re.I)


def health_findings(doc, rel, url):
    out = []
    if url in LEGAL_PAGES:
        return out
    # Blog and the peptides education hub are editorial: they discuss the
    # regulatory landscape, so efficacy vocabulary appears in description rather
    # than as a product claim. Money pages keep the full WARN.
    demote = url.startswith("/blog/") or url.startswith("/peptides/")
    for chunk, line in doc.text:
        for sentence in re.split(r"(?<=[.!?])\s+", chunk):
            if NEGATED.search(sentence):
                continue
            c_probe = (sentence if url.startswith("/peptides/")
                       else REG_SCOPE.sub(" ", sentence))
            b, c = TIER_B.search(sentence), TIER_C.search(c_probe)
            # Only strip the rhetorical 'treat as' when no condition is named.
            probe = sentence if b else TREAT_AS.sub(" ", sentence)
            a = TIER_A.search(probe)
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


def stray_html(root):
    """HTML that lives outside public/ and is not an allowed non-served file.

    html_files() walks public/ only, so no other check in this validator can
    see a page sitting at the repo root.
    """
    out = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs
                   if not d.startswith(".") and d not in ("node_modules", "public")]
        for f in files:
            if not f.endswith(".html"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, f), root).replace(os.sep, "/")
            if rel.startswith(NON_SERVED_HTML_DIRS):
                continue
            out.append(rel)
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
    if work and (rel == "public/index.html" or rel == "public/404.html"
                 or rel.startswith("public/proposals/")):
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
            elif prof == "marketing" and href != want and url != "/preview-home/":
                # /preview-home/ is the review copy of the production homepage.
                # Its canonical deliberately stays https://nearfront.com/ because
                # promotion copies the CONTENT into production index.html, and on
                # this noindexed host the canonical must point at production.
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

        # These two run on EVERY page, including proposals and the work index.
        # A second container double-counts every event and splits the data, and
        # a tag pasted straight into a page bypasses the container entirely.
        # Require a boundary before GTM- so a doc filename like
        # GA4-GTM-SETUP-RUNBOOK.md does not read as a container ID, and require
        # the ID to end at a boundary so GTM-NFLQTMGP-something is not a match.
        for other in set(re.findall(r"(?<![A-Za-z0-9-])GTM-[A-Z0-9]{5,}(?![A-Za-z0-9-])", d.raw)):
            if other != GTM_ID:
                add(Finding(ERROR, rel, 1, "gtm-foreign",
                            "second container %s; this site uses %s only" % (other, GTM_ID),
                            "Two containers double-count every event and split the reporting. "
                            "Add tags inside the existing container instead."))
        for pat, what in TRACKERS_OUTSIDE_GTM:
            m = re.search(pat, d.raw, re.I)
            if m:
                ln = d.raw[:m.start()].count("\n") + 1
                add(Finding(ERROR, rel, ln, "tracker-outside-gtm",
                            "%s is hard-coded into the page" % what,
                            "Every tag ships through container %s so it stays measurable and "
                            "disclosable. A hard-coded tag double-counts alongside the "
                            "container's, and any new tracker must ship in the same deploy as "
                            "its privacy-policy disclosure. See CLAUDE.md, Measurement."
                            % GTM_ID))

        prof = profile_for(urls[rel], rel, work)
        n = d.raw.count(GTM_ID)
        if prof == "report":
            # Client reports and proposals carry NO container. The container
            # loads GA4, RB2B person-level identification and other vendor tags,
            # none of which belong on a page a client opens to read their own
            # confidential report. Enforced here so it cannot quietly come back.
            if n or "googletagmanager" in d.raw:
                add(Finding(ERROR, rel, 1, "reports-no-analytics",
                            "client report page loads the GTM container",
                            "Remove the GTM head snippet and the noscript iframe. "
                            "These pages must not be tracked."))
            continue
        if n < 2:
            add(Finding(ERROR, rel, 1, "gtm",
                        "expected the GTM head snippet and the noscript iframe (%s appears %d time(s))"
                        % (GTM_ID, n),
                        "Copy both blocks from public/%s." % SHELL_REF))

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

    # --- US spelling -------------------------------------------------------
    for rel in in_scope:
        d = docs.get(rel)
        if d is None or profile_for(urls[rel], rel, work) != "marketing":
            continue
        for i, line in enumerate(d.raw.splitlines(), 1):
            for pat, us in BRITISH_SPELLINGS:
                m = re.search(pat, line, re.I)
                if m:
                    add(Finding(WARN, rel, i, "british-spelling",
                                'British spelling "%s" in %s'
                                % (m.group(0), line.strip()[:60]),
                                'Use the US form (%s). Nearfront is a US agency '
                                "writing for US businesses." % us))
                    break

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

    def load_doc(root_dir, relpath, addf):
        path = os.path.join(root_dir, relpath)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = fh.read()
            d = Doc()
            d.feed(raw)
            d.raw = raw
            return d
        except Exception as e:
            addf(Finding(WARN, relpath, 0, "unreadable", str(e)))
            return None

    # --- brand + shared shell ---------------------------------------------
    # The shell reference lives in production. The work lane has no copy of it,
    # so fall back to the landing-page template, whose nav and footer are the
    # same verbatim blocks. Without this the comparison below silently does
    # nothing on the exact lane where hand-written navs get introduced.
    ref, ref_label = docs.get("public/" + SHELL_REF), SHELL_REF
    if ref is None:
        for cand in SHELL_FALLBACKS:
            d = load_doc(root, cand, add)
            if d is not None and d.has_site_nav and d.has_site_footer:
                ref, ref_label = d, cand
                break
    if ref is None and any(profile_for(urls[r], r, work) == "marketing" for r in in_scope):
        add(Finding(ERROR, "scripts/validate.py", 1, "brand-shell-noref",
                    "no shell reference found (tried public/%s, %s)"
                    % (SHELL_REF, ", ".join(SHELL_FALLBACKS)),
                    "Without a reference the nav/footer comparison cannot run and "
                    "hand-written shells ship unchecked. Restore one of those files."))
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
                                "%s links differ from %s: %s"
                                % (label, ref_label, "; ".join(bits)),
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

    # --- shingle overlap between programmatic siblings ---------------------
    # The whole state/city program lives or dies on whether the pages are
    # genuinely different. Template reuse is fine; recycled prose is not.
    geo = [r for r in pages if any(url_for(r).lstrip("/").startswith(p)
                                   for p in GEO_PREFIXES)]
    if len(geo) > 1:
        shell = shingles(docs["public/" + SHELL_REF].raw) if "public/" + SHELL_REF in docs else set()
        sets = {}
        for rel in geo:
            d = docs.get(rel)
            if d is not None:
                sets[rel] = shingles(d.raw) - shell
        seen_pairs = set()
        for a in geo:
            for b in geo:
                if a >= b or a not in sets or b not in sets:
                    continue
                # group siblings by shared prefix; unlike families need no check
                pa = next((p for p in GEO_PREFIXES if url_for(a).lstrip("/").startswith(p)), "")
                pb = next((p for p in GEO_PREFIXES if url_for(b).lstrip("/").startswith(p)), "")
                if pa != pb:
                    continue
                if changed is not None and a not in changed and b not in changed:
                    continue
                union = sets[a] | sets[b]
                if not union:
                    continue
                j = len(sets[a] & sets[b]) / float(len(union))
                key = (a, b)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                if j >= SHINGLE_ERROR or j >= SHINGLE_WARN:
                    sev = ERROR if j >= SHINGLE_ERROR else WARN
                    add(Finding(sev, a, 1, "shingle-overlap",
                                "%.0f%% of the body text is shared with %s"
                                % (j * 100, url_for(b)),
                                "Sibling pages must differ in substance, not just place names. "
                                "Vary the statistics selected, the questions answered, and the "
                                "local detail. Threshold: warn at %d%%, fail at %d%%."
                                % (SHINGLE_WARN * 100, SHINGLE_ERROR * 100)))

    # --- html uploaded outside public/ -------------------------------------
    # Cloudflare Pages serves public/ and nothing else, so a page dropped
    # anywhere else is unreachable while every other signal still reports
    # success: GitHub accepts the commit, Pages builds green, and every check
    # above walks public/ so none of them ever sees the file. Two client
    # reports sat unreachable for a week exactly this way. This is the only
    # check that looks outside public/.
    for rel in stray_html(root):
        add(Finding(ERROR, rel, 1, "stray-root-html",
                    "HTML outside public/, so Cloudflare Pages never serves it",
                    "Move it to public/<path>/index.html. Client reports belong at "
                    "public/reports/<slug>/index.html. Uploading through the GitHub "
                    "web UI drops files at the repo root, which is the usual cause. "
                    "If the file is not meant to be a page, put it under templates/, "
                    "content/, or reference/."))

    # --- audit checks added 2026-09-08 (plan workstream F) -----------------
    def is_geo(rel):
        u = url_for(rel).lstrip("/")
        return any(u.startswith(p) for p in GEO_PREFIXES) and not any(x in u for x in GEO_EXCLUDE)

    def visible(fragment):
        return re.sub(r"\s+", " ", html_unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()

    def shell_pairs(raw, tag, cls):
        m = re.search(r"<%s class=\"%s\".*?</%s>" % (tag, cls, tag), raw, re.S)
        if not m:
            return None
        return [(h, visible(t)) for h, t in re.findall(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', m.group(0), re.S)]

    ref_doc = docs.get("public/" + SHELL_REF)
    ref_nav = shell_pairs(ref_doc.raw, "nav", "site-nav") if ref_doc else None
    ref_foot = shell_pairs(ref_doc.raw, "footer", "site-footer") if ref_doc else None

    for rel in in_scope:
        d = docs.get(rel)
        if d is None or profile_for(urls[rel], rel, work) != "marketing":
            continue
        url = urls[rel]

        # ai-tell: machine-sounding vocabulary in visible text (advisory)
        for text, ln in (d.text if not url.startswith("/peptides/") else []):
            for pat in AI_TELLS:
                mm = re.search(pat, text, re.I)
                if mm and mm.group(0)[0].isupper() and mm.start() > 0:
                    continue   # capitalized mid-sentence: a proper noun such as a program name
                if mm:
                    add(Finding(WARN, rel, ln, "ai-tell",
                                'reads as machine-written: "%s" in %s' % (mm.group(0), text.strip()[:70]),
                                "Say the plain thing. The humanizer pass keeps facts and sources and rewrites the sentence."))
                    break

        # geo-freshness: the note under the scorecard must carry the data date and the read date
        if is_geo(rel) and url not in GEO_DEMO_PAGES and 'class="geo-scorecard"' in d.raw:
            i = d.raw.find('class="geo-scorecard"')
            j = d.raw.find('class="svc-note"', i)
            note = visible(d.raw[j:d.raw.find("</p>", j)]) if j > 0 else ""
            if not note:
                add(Finding(ERROR, rel, 1, "geo-freshness", "scorecard has no dated source note",
                            "Add <p class=\"svc-note\"> under the scorecard naming the agency file, its date, and the day it was read."))
            else:
                if not RETRIEVED_RE.search(note):
                    add(Finding(ERROR, rel, 1, "geo-freshness", "source note lacks a read-on date",
                                'State the day the file was read, e.g. "read on 24 August 2026".'))
                if not SOURCE_DATE_RE.search(note):
                    add(Finding(ERROR, rel, 1, "geo-freshness", "source note lacks the data date",
                                'State what the file covers, e.g. "dated 18 August 2026" or "as of 30 June 2026".'))

        # evidence-links: pages that make dated third-party claims must link at least one source
        jl = " ".join(t for t, _ in d.jsonld)
        evidence = (url.startswith("/vs/") and url != "/vs/") or url in EVIDENCE_PAGES \
            or (('"Article"' in jl or '"BlogPosting"' in jl) and not url.startswith("/peptides/"))
        if evidence:
            ext = [h for h, _t, _l in d.links if h.startswith("http")
                   and not re.match(r"https?://(www\.)?(nearfront\.com|app\.nearfront\.com|www\.googletagmanager\.com)", h)]
            if not ext:
                add(Finding(WARN, rel, 1, "evidence-links", "no outbound source on an evidence-bearing page",
                            "Link the document each claim came from. Competitor artifacts get rel=\"nofollow noopener\"."))

        # faq-sync: the visible FAQ and the FAQPage copy must hold the same questions AND the
        # same text. Google requires the marked-up answer to match what the reader sees; a count
        # check alone missed three answers on the money page whose linked closing sentence was
        # visible but absent from the markup (found and fixed 2026-09-09 with plan C1).
        if '"FAQPage"' in jl:
            q = len(re.findall(r'"@type":\s*"Question"', jl))
            v = d.raw.count("svc-faq-item")
            if v and q != v:
                add(Finding(ERROR, rel, 1, "faq-sync", "FAQPage has %d questions but the page shows %d" % (q, v),
                            "Every visible .svc-faq-item needs a matching Question in the JSON-LD, and vice versa."))
            elif v:
                def _flat(s):
                    return " ".join(html_unescape(re.sub(r"<[^>]+>", "", s)).split())
                vis = re.findall(r'<div class="svc-faq-item"><h3>(.*?)</h3>\s*<p>(.*?)</p>\s*</div>',
                                 d.raw, re.S)
                pairs = []
                for blob in re.findall(r'<script type="application/ld\+json">(.*?)</script>', d.raw, re.S):
                    try:
                        doc = json.loads(blob)
                    except Exception:
                        continue
                    for node in (doc.get("@graph", [doc]) if isinstance(doc, dict) else []):
                        if isinstance(node, dict) and node.get("@type") == "FAQPage":
                            for qn in node.get("mainEntity", []):
                                pairs.append((qn.get("name", ""),
                                              (qn.get("acceptedAnswer") or {}).get("text", "")))
                if len(vis) == len(pairs):
                    for (vq, va), (jq, ja) in zip(vis, pairs):
                        for label, seen, marked in (("question", vq, jq), ("answer", va, ja)):
                            if _flat(seen) != " ".join(html_unescape(marked).split()):
                                add(Finding(ERROR, rel, 1, "faq-sync",
                                            "FAQ %s text differs between the page and the JSON-LD: %s"
                                            % (label, _flat(seen)[:70]),
                                            "The marked-up text must match what the reader sees, "
                                            "anchor text included."))

        # hub-faq: hub and service pages carry a visible FAQ (enabled with plan C1)
        if HUB_FAQ_ENABLED and url in HUB_FAQ_PAGES:
            if '"FAQPage"' not in jl or d.raw.count("svc-faq-item") < 3:
                add(Finding(WARN, rel, 1, "hub-faq", "hub page has no visible FAQ block with FAQPage markup"))

        # og-image-default: the SVG logo does not render as a social preview
        og = d.metas.get("og:image")
        if og and str(og[0]).endswith("logo.svg"):
            add(Finding(WARN, rel, og[1], "og-image-default", "og:image is the SVG logo",
                        "Facebook and LinkedIn do not render SVG previews. Point og:image at a 1200x630 PNG under /og/."))

        # brand-shell-text: nav and footer must match SHELL_REF on (href, text), not only on hrefs
        if ref_nav is not None and rel != "public/" + SHELL_REF:
            for label, want, got in (("nav", ref_nav, shell_pairs(d.raw, "nav", "site-nav")),
                                     ("footer", ref_foot, shell_pairs(d.raw, "footer", "site-footer"))):
                if got is not None and want is not None and got != want:
                    add(Finding(ERROR, rel, 1, "brand-shell-text",
                                "%s links differ from %s in href or label" % (label, SHELL_REF),
                                "Copy the nav and footer verbatim from the shell reference."))

    # count-drift / hub-order: the markets hub is the count and order of record
    hub_rel = "public/markets/index.html"
    hub = docs.get(hub_rel)
    if hub is not None:
        cards = re.findall(r'<a class="mk-card" href="(/cannabis-seo-[a-z-]+/)"', hub.raw)
        li = re.search(r'"itemListElement":\s*\[(.*?)\]', hub.raw, re.S)
        items = re.findall(r'"url":\s*"https://nearfront\.com(/cannabis-seo-[a-z-]+/)"', li.group(1)) if li else []
        if cards and items and cards != items:
            add(Finding(WARN, hub_rel, 1, "hub-order", "ItemList order differs from the card order",
                        "Renumber the ListItems to follow the cards top to bottom."))
        n = len(items) or len(cards)
        count_re = re.compile(r"\b(\d+)\s+(?:sourced |state and city |dispensary |cannabis )*(?:market )?(?:guides|markets)\b", re.I)
        for f in COUNT_DRIFT_FILES:
            fp = os.path.join(root, f)
            if not os.path.exists(fp):
                continue
            with open(fp, "r", encoding="utf-8") as fh:
                txt = fh.read()
            for mm in count_re.finditer(txt):
                if int(mm.group(1)) != n:
                    add(Finding(WARN, f, txt[:mm.start()].count("\n") + 1, "count-drift",
                                'says "%s" but the markets hub lists %d guides' % (mm.group(0), n),
                                "Update the number, or let the hub be the single source of truth."))

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
