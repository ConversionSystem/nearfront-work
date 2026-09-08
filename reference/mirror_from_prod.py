#!/usr/bin/env python3
"""Mirror every page that exists in BOTH lanes from production into the work lane.

The only intended differences between a promoted page and its work-lane draft are
the robots meta (production index,follow; work noindex,nofollow) and, on
/get-started/, the Google Places browser key, which drafts must not carry.
Everything else (nav, copy, JSON-LD) should be identical, so copying production
over the draft is the correct direction once a page has been promoted.

Skipped on purpose: the work-lane root index (it is the proposals host, not the
homepage), proposals/, reports/, preview-home/, assets/, 404.html, robots.txt,
_headers, sitemap.xml (the work lane must never carry one).

Usage: python3 reference/mirror_from_prod.py [--dry-run]
"""
import os, re, sys
PROD = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "nearfront-repo", "public"))
WORK = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public"))
SKIP_PREFIX = ("proposals", "reports", "preview-home", "assets")
dry = "--dry-run" in sys.argv
changed = same = 0
for root, dirs, files in os.walk(WORK):
    rel = os.path.relpath(root, WORK)
    if rel != "." and rel.split(os.sep)[0] in SKIP_PREFIX:
        dirs[:] = []; continue
    for f in files:
        if f != "index.html" or rel == ".":
            continue
        src = os.path.join(PROD, rel, "index.html")
        dst = os.path.join(root, f)
        if not os.path.exists(src):
            continue
        s = open(src, encoding="utf-8").read()
        s = s.replace('<meta name="robots" content="index,follow">', '<meta name="robots" content="noindex,nofollow">')
        # drafts never carry the Places browser key
        s = re.sub(r'(<meta name="google-places-key" content=")[^"]*(")', r'\1\2', s)
        cur = open(dst, encoding="utf-8").read() if os.path.exists(dst) else None
        if cur == s:
            same += 1; continue
        changed += 1
        print(("would update " if dry else "updated ") + rel)
        if not dry:
            open(dst, "w", encoding="utf-8").write(s)
print(f"{'dry run: ' if dry else ''}{changed} updated, {same} already identical")
