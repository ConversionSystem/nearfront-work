# Nearfront brand voice

The voice source for the human-voice pass (plan Workstream D) and for any rewrite run through `conversion-skills:humanizer`. It sits beside the hard brand rules in `nearfront-repo/CLAUDE.md`, which win on any conflict.

Written 2026-09-10 from a measured baseline rather than from taste. Across the 65 in-scope pages (dropped verticals, legal pages, the homepage and client reports excluded) there were 107 "In short:" blocks, 31 pages where more than half the H2s are questions, 118 runs of four consecutive sentences of near-identical length, and 92 uses of "this page" or "this guide". Those are the patterns this document exists to remove. 91 of the 107 "In short:" blocks sit on the geo guides, three per guide, so that is where the pass starts.

## Who is talking

Guillermo Bravo, in search since 2007 and founder of Foottraffik, the first cannabis-focused SEO company. One practitioner telling a dispensary owner what Google and the state regulator actually say, in a category that cannot buy its way into search. Not a brand describing itself.

## The voice in five rules

1. **Concede first.** Say the inconvenient thing before the argument, then make the case that survives it.
2. **Quote when it matters.** When Google or a regulator said it, use their words in quotation marks, link the page, and never round them into something stronger than they are.
3. **Numbers over adjectives.** A figure carries its source and its date. "680 permanently closed against 460 active", not "a brutal market".
4. **Plain declaratives.** Subject, verb, object. Most sentences say one thing.
5. **Say what is not known.** "Google publishes no guidance on iframe indexing" is a sentence worth writing. An open question stated plainly beats an invented answer.

## Exemplars

From the Map Pack post's correction log:
> An earlier version of this page called the profile "the single biggest lever," which was our phrasing, not Google's, and it is gone.

It names our own mistake, attributes the words exactly, and moves on in one sentence.

From the Map Pack post:
> For a dispensary that sentence lands twice: you cannot buy the ranking, and because of the ads policy you cannot buy the space beside it either.

A consequence specific to cannabis, with no adjective doing the work.

From the citations spoke:
> Here is the concession this page has to make before it makes any argument at all: Google does not name citations as a ranking factor.

Concede-first, about a service we sell. Keep the move and drop the tic: "this page" is one of the self-references this pass limits.

From the citations spoke:
> We sell citation work.

Four words. Varied sentence length is a rule, not an accident.

From the Florida guide's freshness note:
> Florida publishes dispensed volumes rather than revenue, so this page states milligrams and ounces and never a market size in dollars.

A limit of the source, stated as a fact rather than apologized for.

From the Washington guide:
> That is 59.3 percent closed, cumulative since adult-use sales began in 2014 rather than an annual rate.

It heads off the obvious misreading of its own number.

## Sentence length and reading level

- Vary length. Four sentences in a row of roughly the same length read as generated. Follow a long sentence with a short one.
- Most sentences under 25 words, some under 8. A long sentence is fine when it carries a list of real items.
- Write for a dispensary owner or general manager, not an SEO. Explain a term of art (Map Pack, NAP, schema) the first time it appears, or leave it out.

## Structural patterns the pass changes

| Pattern | Rule |
|---|---|
| "In short:" blocks | At most one labeled block per page, where it answers the page's main question. Others lose the label. A block that only restates the section above is cut. A figure that appears nowhere else on the page is kept, in an unlabeled sentence. |
| Question-form H2s | No more than half of a page's H2s. Keep questions that mirror a search ("How many dispensaries does Detroit have?"). Turn section headers phrased as questions ("What wins in Michigan's biggest city market?", "What does Nearfront do for a Detroit dispensary?") into plain statements. |
| "It is not X, it is Y" | At most one per page. Most read better as a plain statement of Y. |
| Triplets | Only when there really are three things. |
| Rhetorical questions | Not in body copy. Questions belong in search-shaped H2s and the FAQ. |
| Throat-clearing openers | Start with the claim. Cut "Here is the thing", "It is worth saying", "Let us be exact". |
| Hedging | One qualifier per claim, and only where the source itself is uncertain. |
| "This page" and "this guide" | At most twice per page. |
| Middots | Never a dash substitute in a sentence. Bylines, stat tiles and labels keep theirs; that is data layout, not voice. |

## Words

**Use:** licensed, storefront, active, permanently closed, trade area, Map Pack, Business Profile, sourced, "as of", "read on".

**Banned:** every pattern in `AI_TELLS` in `nearfront-repo/scripts/validate.py`, enforced by the `ai-tell` check. That list includes leverage, navigate the, unlock, delve, landscape, seamless, robust, crucial, pivotal, holistic, foster, utilize, moreover, furthermore, deep dive, game-changer, elevate, empower, harness and streamline. Missouri's statutory "comprehensive license" is allowed.

**Avoid:** any superlative we cannot source ("leading", "top", "the best"), "guaranteed", and empty intensifiers ("very", "really", "incredibly").

## Hard rules, unchanged by this document

- No em dashes or en dashes anywhere. Use a comma, a period or parentheses. Not a middot.
- No health or efficacy claims.
- US spelling, enforced by the `british-spelling` check.
- Every factual or commercial claim keeps its source link and its date.
- CTA "Get Ranked Free" to `/get-started/`. NAP `550 W B St, 4th Floor, San Diego, CA 92101` and `(760) 829-2735`. "Nubravo LLC" appears only on legal pages.
- No client names on a public page without signed permission.

## What the pass may never change

- **Facts.** Every number, date, URL, quotation and source name survives. `reference/voice_diff.py` blocks a fact that disappears and flags one that appears, and the humanizer's own guardrail applies: a rewrite that would change a claim stops and is flagged.
- **JSON-LD.** The pass never edits it. When a visible FAQ answer changes, the FAQPage mirror is updated in a separate mechanical step and `faq-sync` confirms the text matches.
- **A figure that lives only in an "In short:" block.** Dropping the label is fine. Losing the number is not.
- **Uniqueness between guides.** `repeated-sentence` runs on every batch, so a new phrasing rolled out identically across guides fails, by design.
