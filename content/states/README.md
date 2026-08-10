# State facts files

One JSON file per state. These are the source of truth for every number that appears on a `/cannabis-seo-{state}/` page, and later for the `Dataset` schema block on that page.

## The rule that makes this worth doing

**No number reaches a page without a `source_url` and a `retrieved` date in this file.** Not one. If a stat cannot be traced to a primary source, it goes in `gaps` and the page is written without it.

This is the whole competitive thesis for the state program. Bud Authority runs 136 geo pages carrying roughly 30 statistics each, and their citable numbers are self-attributed to their own unpublished analyses ("2024 BudAuthority analysis of 200 cannabis queries"). Impressive-looking, entirely uncheckable. Ours cite state cannabis control commissions and departments of revenue, with dates. Same AI-citability, and it survives scrutiny.

## Field contract

| Field | Meaning |
|---|---|
| `id` | Stable slug, referenced from page copy and from `used_on` |
| `claim` | What the number measures, in plain words |
| `value` | The number, or an object for multi-part facts |
| `unit` | percent, retailers, USD, date, licenses |
| `as_of` | When the fact was true, which is NOT when we looked it up |
| `source_name` | The publishing body, named the way it will be cited on the page |
| `source_url` | Primary source. State agency or statute, never an aggregator |
| `retrieved` | When we fetched it |
| `verify` | How to re-check it. An API query string is ideal |
| `note` | Traps, caveats, context |
| `used_on` | Pages consuming this fact. Keeps sibling pages from reusing the same subset |

`status`: `ready` means enough verified facts exist to write the page. `partial` means blocking gaps remain.

## What went wrong already, and why the format has `note`

**Maryland.** The Comptroller's own cannabis page states a 9 percent rate. It is stale. The rate rose to 12 percent on 2025-07-01 under the Budget Reconciliation and Financing Act of 2025, confirmed by that same office's quarterly revenue reports. An authoritative-looking page was wrong, and only cross-checking caught it.

**California.** A retailer count of 1,560 appeared in search results attributed to DCC rulemaking. Fetching that rulemaking document showed no such number. It stays in `gaps` and does not get published.

Both cases would have shipped as confident, wrong, citable statistics. Assume every convenient number is stale until a primary source says otherwise.

## Sources by state

| State | Licenses | Tax | Local control |
|---|---|---|---|
| CA | DCC (search.cannabis.ca.gov, data dashboards) | CDTFA cannabis guide | DCC local-jurisdiction database |
| MD | Maryland Cannabis Administration dashboard | Comptroller quarterly reports, NOT the static page | MCA guidance, zoning not bans |
| NY | OCM Current Licenses, data.ny.gov `jskf-tt3q`, Socrata API | NYS Dept of Taxation and Finance | OCM opt-out list |
| OR | OLCC via data.oregon.gov `kctd-stii`, Socrata API | Oregon DOR marijuana pages | OLCC opted-out jurisdictions |

NY and OR expose Socrata APIs, so their numbers are re-verifiable in one command and are the cheapest states to keep current. Prefer them for the first pilots.

## Refresh cadence

Tax rates and legality change mid-year and mid-quarter. Re-verify before any state page is edited, and on a fixed quarterly sweep regardless. The hemp and THC-A cohort moves fastest and gets its own quarterly re-check.
