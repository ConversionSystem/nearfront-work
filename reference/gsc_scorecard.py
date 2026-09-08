#!/usr/bin/env python3
"""Turn a Search Console export folder into the monthly scorecard.

    python3 reference/gsc_scorecard.py /Users/steve/NearFront/gsc/2026-09-08
    python3 reference/gsc_scorecard.py <folder> --md out.md --json out.json

Reads the site-wide Performance zip (Queries.csv, Pages.csv, Countries.csv,
Devices.csv, Filters.csv) and any page-filtered Performance zips placed in the
same folder and named per README (…-money.zip, …-geo.zip, …-dispensary-seo.zip,
…-cannabis-seo-agency.zip). Prints, in order: totals, the per-family table with
core and dropped separated, the tracked-term table, the cannibalization table
(or "not pulled"), the intent clusters, the coverage checks against the G7
criteria, and a ledger row. Stdlib only, no network.

Families are URL regexes (recorded in TRACKING-METRICS-STRATEGY.md). A URL that
is in the sitemap belongs to the first family whose regex matches it. A URL not
in the sitemap that matches a _redirects source is legacy-301; anything else is
other (subdomains, parameters, stray paths).
"""
import argparse
import csv
import io
import json
import os
import re
import sys
import zipfile
from collections import OrderedDict, defaultdict
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SITEMAP = os.path.normpath(os.path.join(HERE, "..", "..", "nearfront-repo", "public", "sitemap.xml"))
DEFAULT_REDIRECTS = os.path.normpath(os.path.join(HERE, "_redirects"))

# Order matters: first match wins.
FAMILIES = OrderedDict([
    ("home", r"^/$"),
    ("money", r"^/services/(cannabis-dispensary-seo/)?$"),
    ("commercial-new", r"^/(dispensary-seo|cannabis-seo-agency)/$"),
    ("pillar", r"^/dispensary-marketing/$"),
    ("playbook", r"^/(dispensary-(google-business-profile|google-reviews|local-citations|local-schema|website|menu-seo|multi-location-seo|keyword-research|ai-search|weedmaps-vs-leafly|weedmaps-alternative|tracking-attribution)/|blog/dispensary-near-me-map-pack/)$"),
    ("geo", r"^/(cannabis-seo-(?!agency/)[a-z0-9-]+/|markets/)$"),
    ("vs", r"^/vs/"),
    ("proof", r"^/(how-we-rank-ourselves|dispensary-map-pack-benchmark|dispensary-near-gresham)/$"),
    # Retired 2026-09-08 with the self-reporting posture. Both now 301, so their
    # residual impressions belong with the other redirecting URLs, not with core.
    ("retired", r"^/blog/(eight-weeks-30-market-guides|first-search-console-numbers)/$"),
    ("funnel", r"^/(get-started|book)/$"),
    ("dropped", r"^/(peptides/|thca-seo-|services/(?!cannabis-dispensary-seo/)[^/]+/|blog/(?!dispensary-near-me-map-pack/)[^/]+/)"),
    ("site", r"^/(about-us|our-story|blog|seo-rockstars-podcast|privacy-policy|master-subscription-agreement)/$"),
])
CORE = ("home", "money", "commercial-new", "pillar", "playbook", "geo", "vs", "proof", "funnel", "site")

BRAND = re.compile(r"nearfront|near front|guillermo|bravo|foottraffik|seo rockstars", re.I)
CANNABIS = re.compile(r"dispensar|cannabis|marijuana|weed|thc|420", re.I)
GEO_TOKENS = re.compile(r"seattle|columbia|baltimore|boston|brooklyn|manhattan|queens|new york|nyc|portland|denver|detroit|kansas city|phoenix|minneapolis|orlando|miami|los angeles|san jose|san diego|california|washington|massachusetts|connecticut|nevada|las vegas|oregon|maryland|michigan|arizona|missouri|minnesota|illinois|colorado|florida|new jersey|ohio|new mexico|delaware|maine|montana|vermont|alaska|rhode island|virginia|texas|oklahoma|pennsylvania|new england", re.I)

# Order matters: the day-30 summary counts TRACKED[:6] as the core terms.
# Revised for update #3 on 2026-09-08, after /dispensary-seo/, /cannabis-seo-agency/
# and the full 13-spoke playbook went live in one day.
TRACKED = [
    ("local seo for cannabis dispensaries", "home"),
    ("dispensary seo", "/dispensary-seo/ (moved off the money page; page live 2026-09-08)"),
    ("cannabis dispensary seo", "money page"),
    ("cannabis seo agency", "/cannabis-seo-agency/ (page live 2026-09-08)"),
    ("dispensary marketing", "pillar"),
    ("how to rank a dispensary on google maps", "map pack post (sixth slot, assigned by rule from export #1)"),
    # Recorded beside the core six, never counted in it.
    ("dispensary local seo", "home (family volume leader: 100 impressions in export #1 against 42 for the tracked head)"),
    ("dispensary map pack ranking", "long-tail beside the sixth slot"),
    ("cannabis keywords", "/dispensary-keyword-research/ (spoke 9, live 2026-09-08)"),
    ("dispensary menu seo", "/dispensary-menu-seo/ (spoke 7, live 2026-09-08)"),
]
# Retired 2026-09-08 after their final read in export #1, both at zero impressions:
# "thca seo" and "peptide seo agency". Both verticals were dropped in Aug 2026.

# One service-style head plus one data long-tail per guide. This pair is the
# doorway test the geo program set for itself: if the heads keep earning nothing
# while the data questions carry the family, the titles follow the data.
GEO_TRACKED = [
    ("cannabis seo seattle", "/cannabis-seo-seattle/ (guide live 2026-09-08, no baseline yet)"),
    ("how many dispensaries in seattle", "/cannabis-seo-seattle/ long-tail"),
    ("cannabis seo columbia md", "/cannabis-seo-columbia-md/ (guide live 2026-09-08, no baseline yet)"),
    ("how many dispensaries in columbia md", "/cannabis-seo-columbia-md/ long-tail"),
    ("cannabis seo oregon", "/cannabis-seo-oregon/"),
    ("dispensary seo oregon", "/cannabis-seo-oregon/"),
    ("cannabis seo colorado", "/cannabis-seo-colorado/"),
    ("dispensary seo colorado", "/cannabis-seo-colorado/"),
    ("dispensary seo ny", "/cannabis-seo-new-york/"),
]
CANNIBAL_QUERIES = ["dispensary seo", "dispensary seo agency", "dispensary seo services", "dispensary seo company",
                    "cannabis dispensary seo", "cannabis seo", "cannabis seo agency", "cannabis seo company",
                    "marijuana seo services", "local seo for cannabis dispensaries"]
INTERNAL_COUNTRIES = ("Slovakia",)  # this environment's headless browsing geolocates there


def num(s):
    s = (s or "").strip().replace(",", "").rstrip("%")
    try:
        return float(s)
    except ValueError:
        return 0.0


def read_zip(path):
    out = {}
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if not name.lower().endswith(".csv"):
                continue
            with z.open(name) as fh:
                text = io.TextIOWrapper(fh, encoding="utf-8-sig").read()
            rows = list(csv.reader(io.StringIO(text)))
            out[os.path.basename(name)] = rows
    return out


def perf_rows(rows):
    """-> list of dicts keyed by name/clicks/prev_clicks/impr/prev_impr/ctr/prev_ctr/pos/prev_pos"""
    if not rows:
        return []
    hdr = rows[0]
    has_prev = any("Previous" in h for h in hdr)
    out = []
    for r in rows[1:]:
        if not r or not r[0].strip():
            continue
        r[0] = re.sub(r"\s+", " ", r[0]).strip()
        if has_prev:
            d = dict(name=r[0], clicks=num(r[1]), prev_clicks=num(r[2]), impr=num(r[3]), prev_impr=num(r[4]),
                     ctr=num(r[5]), prev_ctr=num(r[6]), pos=num(r[7]), prev_pos=num(r[8]))
        else:
            d = dict(name=r[0], clicks=num(r[1]), prev_clicks=0.0, impr=num(r[2]), prev_impr=0.0,
                     ctr=num(r[3]), prev_ctr=0.0, pos=num(r[4]), prev_pos=0.0)
        out.append(d)
    return out


def sitemap_paths(path):
    if not os.path.exists(path):
        return set()
    txt = open(path, encoding="utf-8").read()
    return {urlsplit(u).path for u in re.findall(r"<loc>([^<]+)</loc>", txt)}


def redirect_sources(path):
    src = set()
    if not os.path.exists(path):
        return src
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            src.add(parts[0])
    return src


def family_of(url, sitemap, redirects):
    u = urlsplit(url)
    host, p = u.netloc.lower(), u.path or "/"
    if host not in ("nearfront.com", "www.nearfront.com"):
        return "other"
    if p in sitemap:
        for fam, rx in FAMILIES.items():
            if re.search(rx, p):
                return fam
        return "site"
    if p in redirects or p.rstrip("/") in redirects or (p + "/") in redirects:
        return "legacy-301"
    return "other"


def wpos(rows):
    n = sum(r["impr"] for r in rows)
    return (sum(r["pos"] * r["impr"] for r in rows) / n) if n else 0.0


def pct(a, b):
    return (100.0 * a / b) if b else 0.0


def find_zip(folder, *needles):
    for f in sorted(os.listdir(folder)):
        fl = f.lower()
        if fl.endswith(".zip") and all(n in fl for n in needles):
            return os.path.join(folder, f)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--sitemap", default=DEFAULT_SITEMAP)
    ap.add_argument("--redirects", default=DEFAULT_REDIRECTS)
    ap.add_argument("--md", help="write the markdown report here as well as stdout")
    ap.add_argument("--json", help="write the numbers here")
    a = ap.parse_args()

    export_date = os.path.basename(os.path.normpath(a.folder))
    site_zip = find_zip(a.folder, "performance-on-search") or find_zip(a.folder, "performance")
    if not site_zip:
        sys.exit("no Performance zip in %s" % a.folder)
    Z = read_zip(site_zip)
    queries = perf_rows(Z.get("Queries.csv", []))
    pages = perf_rows(Z.get("Pages.csv", []))
    countries = perf_rows(Z.get("Countries.csv", []))
    devices = perf_rows(Z.get("Devices.csv", []))
    filters = {r[0]: r[1] for r in Z.get("Filters.csv", [])[1:] if len(r) >= 2}
    sitemap = sitemap_paths(a.sitemap)
    redirects = redirect_sources(a.redirects)

    out, J = [], {"export": export_date, "filters": filters}
    def P(s=""):
        out.append(s)

    # 1. totals -------------------------------------------------------------
    t_impr = sum(r["impr"] for r in devices) or sum(r["impr"] for r in pages)
    t_clicks = sum(r["clicks"] for r in devices) or sum(r["clicks"] for r in pages)
    p_impr = sum(r["prev_impr"] for r in devices)
    p_clicks = sum(r["prev_clicks"] for r in devices)
    internal = [r for r in countries if r["name"] in INTERNAL_COUNTRIES]
    int_clicks = sum(r["clicks"] for r in internal)
    P("# Search Console scorecard, export %s" % export_date)
    P()
    P("Filters: %s. Period: last 3 months against the previous 3 months, device totals." % ", ".join("%s=%s" % kv for kv in filters.items()))
    P()
    P("| Total | Last 3 months | Previous 3 months |")
    P("|---|---|---|")
    P("| Impressions | %d | %d |" % (t_impr, p_impr))
    P("| Clicks | %d | %d |" % (t_clicks, p_clicks))
    P("| CTR | %.2f%% | %.2f%% |" % (pct(t_clicks, t_impr), pct(p_clicks, p_impr)))
    P("| Position (impression-weighted, pages) | %.1f | %.1f |" % (wpos(pages), (sum(r["prev_pos"] * r["prev_impr"] for r in pages) / p_impr) if p_impr else 0))
    for d in devices:
        P("| %s share of impressions | %.0f%% | %.0f%% |" % (d["name"], pct(d["impr"], t_impr), pct(d["prev_impr"], p_impr)))
    P("| Distinct queries in export | %d | n/a |" % len(queries))
    if internal:
        P("| Internal test traffic (%s) | %d clicks, %d impressions | %d clicks |" % (", ".join(r["name"] for r in internal), int_clicks, sum(r["impr"] for r in internal), sum(r["prev_clicks"] for r in internal)))
    J["totals"] = dict(impr=t_impr, clicks=t_clicks, prev_impr=p_impr, prev_clicks=p_clicks, internal_clicks=int_clicks, queries=len(queries))
    P()

    # 2. families -----------------------------------------------------------
    fam_rows = defaultdict(list)
    for r in pages:
        fam_rows[family_of(r["name"], sitemap, redirects)].append(r)
    fam_pages = defaultdict(set)
    for p in sitemap:
        for fam, rx in FAMILIES.items():
            if re.search(rx, p):
                fam_pages[fam].add(p)
                break
        else:
            fam_pages["site"].add(p)
    order = list(FAMILIES.keys()) + ["legacy-301", "other"]
    P("## By page family (core and dropped reported separately)")
    P()
    P("| Family | Pages | With impressions | Impressions | Prev | Clicks | Prev | CTR | Position |")
    P("|---|---|---|---|---|---|---|---|---|")
    J["families"] = {}
    core_i = core_c = core_pi = core_pc = 0
    drop_i = drop_c = drop_pi = drop_pc = 0
    for fam in order:
        rows = fam_rows.get(fam, [])
        n_pages = len(fam_pages.get(fam, ())) if fam in FAMILIES else len(rows)
        with_impr = sum(1 for r in rows if r["impr"] > 0)
        i, c, pi, pc = (sum(r[k] for r in rows) for k in ("impr", "clicks", "prev_impr", "prev_clicks"))
        if fam in CORE:
            core_i += i; core_c += c; core_pi += pi; core_pc += pc
        elif fam == "dropped":
            drop_i += i; drop_c += c; drop_pi += pi; drop_pc += pc
        P("| %s | %d | %d | %d | %d | %d | %d | %.2f%% | %.1f |" % (fam, n_pages, with_impr, i, pi, c, pc, pct(c, i), wpos(rows)))
        J["families"][fam] = dict(pages=n_pages, with_impr=with_impr, impr=i, prev_impr=pi, clicks=c, prev_clicks=pc, pos=round(wpos(rows), 1),
                                  urls=sorted(((r["name"], r["impr"], r["clicks"], r["pos"]) for r in rows), key=lambda x: -x[1]))
    P("| **core (all families above except dropped, legacy-301, other)** | | | **%d** | %d | **%d** | %d | %.2f%% | |" % (core_i, core_pi, core_c, core_pc, pct(core_c, core_i)))
    P("| **dropped** | | | **%d** | %d | **%d** | %d | %.2f%% | |" % (drop_i, drop_pi, drop_c, drop_pc, pct(drop_c, drop_i)))
    leg = fam_rows.get("legacy-301", [])
    P("| **legacy-301** | | | **%d** | %d | **%d** | %d | | |" % (sum(r["impr"] for r in leg), sum(r["prev_impr"] for r in leg), sum(r["clicks"] for r in leg), sum(r["prev_clicks"] for r in leg)))
    P()
    P("Legacy share of impressions: %.0f%%. Core per day (last 3 months, 92 days): %.1f impressions." % (pct(sum(r["impr"] for r in leg), t_impr), core_i / 92.0))
    J["core"] = dict(impr=core_i, clicks=core_c, prev_impr=core_pi, prev_clicks=core_pc, per_day=round(core_i / 92.0, 1))
    J["dropped"] = dict(impr=drop_i, clicks=drop_c, prev_impr=drop_pi, prev_clicks=drop_pc)
    P()
    P("Top legacy URLs still drawing impressions (where the 301 equity sits):")
    P()
    for r in sorted(leg, key=lambda x: -x["impr"])[:8]:
        P("- %s: %d impressions, %d clicks, position %.1f" % (urlsplit(r["name"]).path, r["impr"], r["clicks"], r["pos"]))
    P()

    # 3. tracked terms --------------------------------------------------------
    qmap = {r["name"].strip().lower(): r for r in queries}
    P("## Tracked terms (site-wide export; GSC average position is the source of record)")
    P()
    def term_table(terms, bucket):
        P("| Term | Target page | Impressions | Clicks | Position | Prev impressions | Prev position |")
        P("|---|---|---|---|---|---|---|")
        for term, target in terms:
            r = qmap.get(term)
            if r:
                P("| %s | %s | %d | %d | %.1f | %d | %s |" % (term, target, r["impr"], r["clicks"], r["pos"], r["prev_impr"], ("%.1f" % r["prev_pos"]) if r["prev_impr"] else "none"))
                bucket[term] = dict(impr=r["impr"], clicks=r["clicks"], pos=r["pos"], prev_impr=r["prev_impr"], prev_pos=r["prev_pos"])
            else:
                P("| %s | %s | 0 | 0 | not shown | 0 | none |" % (term, target))
                bucket[term] = dict(impr=0, clicks=0, pos=None, prev_impr=0, prev_pos=None)
        P()

    J["tracked"] = {}
    term_table(TRACKED, J["tracked"])

    P("### Geo terms (head vs long-tail: the doorway test)")
    P()
    J["geo_tracked"] = {}
    term_table(GEO_TRACKED, J["geo_tracked"])
    heads = [t for t, _ in GEO_TRACKED if t.startswith(("cannabis seo", "dispensary seo"))]
    tails = [t for t, _ in GEO_TRACKED if t not in heads]
    P("- Geo heads with an impression: %d of %d; data long-tails with an impression: %d of %d" % (
        sum(1 for t in heads if J["geo_tracked"][t]["impr"]), len(heads),
        sum(1 for t in tails if J["geo_tracked"][t]["impr"]), len(tails)))
    P()

    # 4. cannibalization ------------------------------------------------------
    P("## Cannibalization monitor (page-filtered exports)")
    P()
    filtered = {}
    for key, needle in (("money", "money"), ("dispensary-seo", "dispensary-seo"), ("cannabis-seo-agency", "cannabis-seo-agency"), ("geo", "-geo")):
        z = find_zip(a.folder, "performance", needle)
        if z:
            filtered[key] = {r["name"].strip().lower(): r for r in perf_rows(read_zip(z).get("Queries.csv", []))}
    if not filtered:
        P("Not pulled this export. Site-wide baseline for the query set (check 0):")
        P()
        P("| Query | Impressions | Clicks | Position |")
        P("|---|---|---|---|")
        for q in CANNIBAL_QUERIES:
            r = qmap.get(q)
            P("| %s | %d | %d | %s |" % (q, r["impr"] if r else 0, r["clicks"] if r else 0, ("%.1f" % r["pos"]) if r else "not shown"))
    else:
        P("| Query | " + " | ".join(filtered.keys()) + " | Owner | Owner share |")
        P("|---|" + "---|" * (len(filtered) + 2))
        for q in CANNIBAL_QUERIES:
            vals = {k: (v[q]["impr"] if q in v else 0) for k, v in filtered.items()}
            tot = sum(vals.values())
            owner = max(vals, key=vals.get) if tot else "none"
            P("| %s | %s | %s | %.0f%% |" % (q, " | ".join("%d" % vals[k] for k in filtered), owner, pct(vals.get(owner, 0), tot)))
    P()

    # 5. intent clusters ------------------------------------------------------
    nb = [r for r in queries if not BRAND.search(r["name"])]
    brand = [r for r in queries if BRAND.search(r["name"])]
    cann = [r for r in nb if CANNABIS.search(r["name"])]
    geo = [r for r in cann if GEO_TOKENS.search(r["name"])]
    off = [r for r in nb if not CANNABIS.search(r["name"])]
    def cl(name, rows):
        P("| %s | %d | %d | %d | %.1f |" % (name, len(rows), sum(r["impr"] for r in rows), sum(r["clicks"] for r in rows), wpos(rows)))
    P("## Query clusters (site-wide; Google withholds rare queries, so these undercount the totals)")
    P()
    P("| Cluster | Queries | Impressions | Clicks | Position |")
    P("|---|---|---|---|---|")
    cl("brand", brand); cl("non-brand, dispensary or cannabis intent", cann); cl("of which geo (market name + cannabis word)", geo); cl("non-brand, off-topic (legacy and dropped topics)", off)
    P()
    top10 = [r for r in nb if r["pos"] <= 10 and r["impr"] > 0]
    top30 = [r for r in nb if r["pos"] <= 30 and r["impr"] > 0]
    top10_on = [r for r in cann if r["pos"] <= 10 and r["impr"] > 0]
    top30_on = [r for r in cann if r["pos"] <= 30 and r["impr"] > 0]
    P("Non-brand queries at position 10 or better: %d, of which %d carry dispensary or cannabis intent (%s). At 30 or better: %d, on-topic %d." % (
        len(top10), len(top10_on), "; ".join("%s %d at %.1f" % (r["name"], r["impr"], r["pos"]) for r in sorted(top10_on, key=lambda x: -x["impr"])[:12]), len(top30), len(top30_on)))
    P()
    P("Top non-brand cannabis-intent queries by impressions:")
    P()
    for r in sorted(cann, key=lambda x: -x["impr"])[:15]:
        P("- %s: %d impressions, %d clicks, position %.1f" % (r["name"], r["impr"], r["clicks"], r["pos"]))
    P()
    P("Top geo queries by impressions:")
    P()
    for r in sorted(geo, key=lambda x: -x["impr"])[:12]:
        P("- %s: %d impressions, %d clicks, position %.1f" % (r["name"], r["impr"], r["clicks"], r["pos"]))
    J["clusters"] = dict(brand=len(brand), cannabis=len(cann), geo=len(geo), off=len(off), top10=len(top10), top30=len(top30), top10_on=len(top10_on), top30_on=len(top30_on),
                         top10_on_list=[(r["name"], r["impr"], r["pos"]) for r in sorted(top10_on, key=lambda x: -x["impr"])],
                         cannabis_impr=sum(r["impr"] for r in cann), geo_impr=sum(r["impr"] for r in geo), off_impr=sum(r["impr"] for r in off))
    P()

    # 6. G7 checks ------------------------------------------------------------
    P("## Day-30 / 60 / 90 criteria, read against this export")
    P()
    fam_has_nb = {fam: any(r["impr"] > 0 for r in fam_rows.get(fam, [])) for fam in CORE}
    P("- Families with at least one impression: %s; without: %s" % (", ".join(f for f, v in fam_has_nb.items() if v) or "none", ", ".join(f for f, v in fam_has_nb.items() if not v) or "none"))
    P("- Core impressions per day: %.1f (Aug 4 figure to beat: 194)" % (core_i / 92.0))
    P("- Non-brand queries in the top 10: %d on-topic (day-60 target 3, day-90 target 10); %d including off-topic legacy queries" % (len(top10_on), len(top10)))
    geo_with = J["families"].get("geo", {}).get("with_impr", 0); geo_n = J["families"].get("geo", {}).get("pages", 0)
    P("- Geo guides with impressions: %d of %d (day-90 target: half)" % (geo_with, geo_n))
    P("- Tracked terms with an impression: %d of 6 core terms" % sum(1 for t, _ in TRACKED[:6] if J["tracked"][t]["impr"]))
    P()

    # 7. ledger row -------------------------------------------------------------
    P("## Ledger row")
    P()
    P("| %s | gsc-scorecard-%s | previous period %d impressions, %d clicks | %d impressions, %d clicks; core %d, dropped %d, legacy %d | monthly export | ~/NearFront/gsc/%s/ | confirmed | Site-wide export parsed by reference/gsc_scorecard.py. Core %.1f impressions per day. Non-brand on-topic top-10 queries: %d. Geo guides with impressions: %d of %d. Tracked: %s. |" % (
        export_date, export_date, p_impr, p_clicks, t_impr, t_clicks, core_i, drop_i, sum(r["impr"] for r in leg), export_date, core_i / 92.0, len(top10_on), geo_with, geo_n,
        "; ".join("%s %s" % (t, ("%d at %.1f" % (J["tracked"][t]["impr"], J["tracked"][t]["pos"])) if J["tracked"][t]["impr"] else "0") for t, _ in TRACKED[:6])))

    text = "\n".join(out) + "\n"
    sys.stdout.write(text)
    if a.md:
        open(a.md, "w", encoding="utf-8").write(text)
    if a.json:
        open(a.json, "w", encoding="utf-8").write(json.dumps(J, indent=2))


if __name__ == "__main__":
    main()
