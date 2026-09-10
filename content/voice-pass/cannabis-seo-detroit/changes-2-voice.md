# Detroit, voice rewrite (human-voice pass, step 3)

Applied to the fully corrected page (`baseline.json`) with `reference/voice_apply.py`, then checked with `reference/voice_diff.py check baseline.json` and the work-lane validator. Voice source: `content/brand-voice.md`. No FAQ answer and no JSON-LD is edited here. The store names in the "Who is already licensed" box sit outside this change set; on 2026-09-10 they were narrowed to the four the city's license list confirms (fact-check row 13).

## V1 hero
Cut the stock transition ("That is the good news. The rest of the story is"). Same four figures, same claim.
<<<
Every eligible Michigan retail license earned its municipality a $54,017.10 excise check this year. Detroit cashed 61 of them, more than any other municipality in the state. That is the good news. The rest of the story is a market that sold $270.5 million statewide in July 2026 at $58.95 an ounce, which means the stores that win in Detroit are not winning on price.
===
Every eligible Michigan retail license earned its municipality a $54,017.10 excise check this year. Detroit cashed 61 of them, more than any other municipality in the state. Its stores compete in a market that sold $270.5 million statewide in July 2026 at $58.95 an ounce, where nobody wins on price.
>>>

## V2 source note
Breaks a run of four same-length sentences by joining the two city sources into one sentence.
<<<
The 61 comes from the Michigan Treasury's FY2025 adult-use distribution file, license counts as of 30 September 2025. The city's own licensing dashboard, queried 24 August 2026, shows 67 retail licenses and 34 medical provisioning centers. The 154 is the building department's open business-license dataset, read the same day. Sales and price figures are from the Cannabis Regulatory Agency's July 2026 monthly report, read 24 August 2026. Three different systems count Detroit three different ways.
===
The 61 comes from the Michigan Treasury's FY2025 adult-use distribution file, license counts as of 30 September 2025. The city's own licensing dashboard, queried 24 August 2026, shows 67 retail licenses and 34 medical provisioning centers, and the building department's open business-license dataset, read the same day, lists the 154. Sales and price figures are from the Cannabis Regulatory Agency's July 2026 monthly report, read 24 August 2026. Three systems count Detroit three different ways.
>>>

## V3 how many dispensaries, paragraph 1
Starts with the claim instead of a fragment, and drops "the honest answer".
<<<
Depends which official list you read, and the honest answer names all three. The Michigan Treasury paid excise distributions on 61 Detroit retail licenses as of September 2025, the largest municipal count in the state. The city's own licensing dashboard showed 67 adult-use retail licenses and 34 medical provisioning centers when we queried it in August 2026. And on 24 August 2026 Detroit's building department listed 154 active marijuana facility licenses of all types, growers and processors included.
===
Three official lists answer that, and they disagree. The Michigan Treasury paid excise distributions on 61 Detroit retail licenses as of September 2025, the largest municipal count in the state. The city's own licensing dashboard showed 67 adult-use retail licenses and 34 medical provisioning centers when we queried it in August 2026. On 24 August 2026 the building department listed 154 active marijuana facility licenses of all types, growers and processors included.
>>>

## V4 how many dispensaries, paragraph 2
Replaces the "not sloppiness, it is three lenses" contrast with the plain statement, and "as it stands today" with the query date.
<<<
The spread is not sloppiness, it is three lenses with three dates: the Treasury counts the retail stores and microbusinesses licensed on 30 September 2025, the dashboard counts current city retail approvals, and the building department counts every facility type it licenses. Any Detroit operator sizing up the competition should count the 67, because that is the retail field as it stands today.
===
The three counts measure different things on different dates: the Treasury counts the retail stores and microbusinesses licensed on 30 September 2025, the dashboard counts current city retail approvals, and the building department counts every facility type it licenses. To size up the competition, count the 67, the retail field as of our August 2026 query.
>>>

## V5 how many dispensaries, paragraph 3
Says what is not published first, then gives the nearest figure.
<<<
For scale, Wayne County as a whole did $30.6 million in adult-use sales in July 2026, about 11 percent of the state's $270.5 million month. The state does not publish city-level sales, so that county figure is the closest official measure of what the Detroit market moves.
===
The state does not publish city-level sales. The closest official measure is Wayne County, which did $30.6 million in adult-use sales in July 2026, about 11 percent of the state's $270.5 million month.
>>>

## V6 the one labeled "In short" block
Kept, because it answers the page's main search question. It now leads with the current retail count and says why the sales figure is a county one.
<<<
<strong>In short:</strong> Michigan's Treasury counted 61 Detroit retail licenses as of September 2025, the largest municipal total in the state. The city dashboard showed 67 retail licenses plus 34 medical provisioning centers in August 2026, and the building department listed 154 facility licenses of all types the same month. Wayne County did $30.6 million in adult-use sales in July 2026.
===
<strong>In short:</strong> The city's dashboard showed 67 adult-use retail licenses and 34 medical provisioning centers in August 2026, and the building department listed 154 facility licenses of all types that month. Michigan's Treasury counted 61 Detroit retail licenses as of September 2025, the most of any municipality in the state. The state publishes no Detroit sales figure; Wayne County did $30.6 million in adult-use sales in July 2026.
>>>

## V7 excise section heading
A question nobody searches, turned into a statement.
<<<
<h2>Why does the excise distribution matter to a dispensary?</h2>
===
<h2>The excise file maps Michigan's retail</h2>
>>>

## V8 excise, paragraph 1
Drops "Because it is the cleanest public measure" (an answer to the old question heading, and an unsourced superlative) and "exactly". The statewide total gets its own clause so it no longer reads as divided across the 860.
<<<
Because it is the cleanest public measure of where Michigan's retail actually sits. Once a year the Treasury divides a share of the state's adult-use excise tax equally among every eligible retail license, $54,017.10 per license for FY2025, and publishes exactly how many licenses each municipality hosts. Detroit's 61 beat every other city in the state. Statewide, $93.8 million went out to municipalities and counties, for 860 licenses in 234 municipalities.
===
Once a year the Treasury divides a share of the state's adult-use excise tax equally among every eligible retail license, $54,017.10 per license for FY2025, and publishes how many licenses each municipality hosts. That makes the file a public record of where Michigan's licensed retail sits. Detroit's 61 beat every other city in the state. Statewide the file lists 860 eligible licenses in 234 municipalities, and the total paid to municipalities and counties together was $93.8 million.
>>>

## V9 excise, paragraph 2
Cuts the throat-clearing opener ("Read that file the way an operator should") and "just".
<<<
Read that file the way an operator should: licensed retail exists in just 234 Michigan municipalities, and every city, village or township that opted out sends its customers somewhere that did not. That concentrates demand into the places that let it in. Detroit is the biggest of those places, and its stores draw from suburbs that opted out.
===
Licensed retail exists in 234 Michigan municipalities. Every city, village or township that opted out sends its customers somewhere that did not, which concentrates demand in the places that let retail in. Detroit is the biggest of those places, and its stores draw from suburbs that opted out.
>>>

## V10 excise, paragraph 3, and the second "In short" block
Cuts "That is a real advantage, and it cuts both ways" and the "moat" metaphor. The "In short" block only restated the section; every figure in it appears above, so it goes.
<<<
That is a real advantage, and it cuts both ways. On Treasury's September 2025 count, the same concentration that pulls customers into Detroit put 60 other licensed stores between them and you. In a market where the average ounce of flower retails at $58.95, nobody sustains a price moat. What separates stores is whether people searching from Dearborn, Southfield or the east side find them first.</p>
    <div class="geo-answer">
      <p><strong>In short:</strong> Michigan's Treasury distributed $93.8 million of FY2025 excise revenue to municipalities and counties, and each of the 860 eligible retail licenses in 234 municipalities earned its municipality $54,017.10. Detroit hosts 61 of those licenses, the most in the state, drawing customers from opted-out suburbs but also concentrating the competition into one city.</p>
    </div>
===
The concentration that pulls customers into Detroit also works against every store in it: on the Treasury's September 2025 count, it put 60 other licensed stores between those customers and you. At $58.95 for the average ounce of flower, no store keeps a price advantage. What separates stores is whether people searching from Dearborn, Southfield or the east side find them first.</p>
>>>

## V11 price section label
"Price is not the moat" was a contrast and the third "moat" on the page.
<<<
<span class="svc-section-tag">Price is not the moat</span>
===
<span class="svc-section-tag">Price and paid media</span>
>>>

## V12 price section heading
<<<
<h2>What does $58.95 an ounce mean for Detroit marketing?</h2>
===
<h2>Marketing a Detroit store at $58.95 an ounce</h2>
>>>

## V13 price, paragraph 1
Drops "own", and splits the closing sentence so the page's short sentences are not all in one place.
<<<
Michigan's average retail flower ounce sold for $58.95 in July 2026, per the Cannabis Regulatory Agency's own monthly report. The same report counts 836 licensed retailers and 875 licensed growers statewide, with 41,257 people working in the industry. Supply is deep, and a competitor can match any discount a Detroit store runs.
===
The average ounce of retail flower in Michigan sold for $58.95 in July 2026, according to the Cannabis Regulatory Agency's monthly report. That report counts 836 licensed retailers and 875 licensed growers statewide, and 41,257 people working in the industry. Supply is deep. A competitor can match any discount a Detroit store runs.
>>>

## V14 price, paragraph 2
"Makes the point brutally" was an adjective doing the work of the number.
<<<
The medical side of the ledger makes the point brutally: licensed medical facilities sold $311,726 statewide in July against $270.5 million adult-use. Medical facility sales are around a tenth of one percent of the total. Nearly all the sales are adult-use, where Detroit's 67 retail licenses sell comparable product.
===
Medical sales barely register. Licensed medical facilities sold $311,726 statewide in July against $270.5 million adult-use, around a tenth of one percent of the total. Nearly all the sales are adult-use, where Detroit's 67 retail licenses sell comparable product.
>>>

## V15 price, paragraph 3, and the third "In short" block
The block restated the section ("the remaining lever", "compounds instead of renting"); its figures appear above.
<<<
In that shape of market, the store a customer sees first is the store that wins the trip. Google and Meta both prohibit paid THC ads, so first position cannot be bought with media spend. It is earned through the Map Pack, reviews, and a site Google trusts.</p>
    <div class="geo-answer">
      <p><strong>In short:</strong> With flower averaging $58.95 an ounce, 836 retailers statewide and paid THC ads prohibited on Google and Meta, price and media cannot differentiate a Detroit dispensary. Visibility when a customer searches is the remaining lever, and it compounds instead of renting.</p>
    </div>
===
In a market shaped like this, the store a customer sees first is the store that wins the trip. Google and Meta both prohibit paid THC ads. No dispensary can buy that first position, so it is earned through the Map Pack, reviews and a site Google trusts.</p>
>>>

## V16 priorities section label
"What moves the needle" is a stock phrase.
<<<
<span class="svc-section-tag">What moves the needle</span>
===
<span class="svc-section-tag">Priorities</span>
>>>

## V17 priorities section heading
<<<
<h2>What wins in Michigan's biggest city market?</h2>
===
<h2>Where to put the work in Detroit</h2>
>>>

## V18 card: stop defending price
The last "moat" goes.
<<<
<p>At $58.95 an ounce statewide, any competitor can match a price cut. A visibility moat, built through reviews and Map Pack position, is the one competitors cannot match overnight.</p>
===
<p>At $58.95 an ounce statewide, any competitor can match a price cut. Reviews and Map Pack position accumulate, and nobody copies those overnight.</p>
>>>

## V19 card: own the opt-out suburbs
Three short sentences in a row become one longer and one short.
<<<
<p>Only 234 Michigan municipalities host licensed retail. Customers in the ones that opted out already drive to Detroit. Rank for the searches they make before they drive. One of those searches is a dispensary near me typed from a town with no store, and <a href="https://support.google.com/business/answer/7091" rel="noopener" target="_blank">Google ranks it from the searcher's location</a>, so a Detroit store reaching those drivers has to win on relevance and prominence as well as distance.</p>
===
<p>Only 234 Michigan municipalities host licensed retail, and customers in the suburbs that opted out already drive to Detroit. Rank for the searches they make before they drive. One of them is dispensary near me, typed from a town with no store: <a href="https://support.google.com/business/answer/7091" rel="noopener" target="_blank">Google ranks it from the searcher's location</a>, so a Detroit store reaching those drivers has to win on relevance and prominence as well as distance.</p>
>>>

## V20 card: count the field
"Honestly" and "a market that does not exist" go; the card says which count to use, as section 2 does.
<<<
<h3>Count the field honestly</h3><p>Three official counts exist: the Treasury's 61 (September 2025), the city dashboard's 67 and the building department's 154 (both August 2026). Sizing your competition from the wrong list means marketing against a market that does not exist.</p>
===
<h3>Count the field from the right list</h3><p>Three official counts exist: the Treasury's 61 (September 2025), the city dashboard's 67 and the building department's 154 (both August 2026). Only the 67 is the current retail field, so size your competition from that one.</p>
>>>

## V21 card: plan for the adult-use customer
The body no longer repeats the new title word for word.
<<<
<p>Statewide medical facility sales were $311,726 in July against $270.5 million adult-use. Every plan should assume the adult-use customer is the customer.</p>
===
<p>Statewide medical facility sales were $311,726 in July against $270.5 million adult-use. Build every campaign for that customer.</p>
>>>

## V22 card: be the named answer
Drops "this page".
<<<
<p>When someone asks an AI assistant for a dispensary on the east side, it does not name all 67. The work on this page is how a store improves its odds of being named.</p>
===
<p>Ask an AI assistant for a dispensary on the east side and it will not name all 67. The work described below is how a store improves its odds of being named.</p>
>>>

## V23 how we work heading
<<<
<h2>What does Nearfront do for a Detroit dispensary?</h2>
===
<h2>What Nearfront does for a Detroit dispensary</h2>
>>>

## V24 how we work, paragraph 1
Drops "actually" and "specific".
<<<
We start with a free data audit that maps your Google Map Pack position across the neighborhoods and suburbs you actually serve, against the specific stores that outrank you there. In Detroit the audit shows how many of the 67 licensed competitors matter in any one part of the city, and where you rank in the suburbs around it.
===
We start with a free data audit. It maps your Google Map Pack position across the neighborhoods and suburbs you serve, against the stores that outrank you in each. In Detroit that shows how many of the 67 licensed competitors matter in any one part of the city, and where you rank in the suburbs around it.
>>>

## V25 how we work, paragraph 2
"Compounding" and "actually type" go; the reported actions are named as profile actions, the term the tracking spoke uses.
<<<
Then the compounding work: Google Business Profile completeness, citation consistency, a review system that runs every week instead of in bursts, menu and site structure that keeps your own domain in the results instead of a third-party menu host, and pages built for the searches people in Dearborn, Southfield, Warren and the Grosse Pointes actually type. Everything is reported against actions, direction requests, calls and menu clicks, not ranking screenshots.
===
Then the work that builds over time: Google Business Profile completeness, citation consistency, a review system that runs every week instead of in bursts, menu and site structure that keeps your own domain in the results instead of a third-party menu host, and pages built for what people in Dearborn, Southfield, Warren and the Grosse Pointes search. We report it against profile actions (direction requests, calls and menu clicks), not ranking screenshots.
>>>

## V26 how we work, paragraph 3
<<<
We do not guarantee positions, because nobody honestly can.
===
We do not guarantee positions, because nobody can.
>>>

## V27 closing call to action
Drops "actually". The first wording, "name the stores competing with you", repeated the Illinois guide and failed repeated-sentence, so it was reworded.
<<<
name the stores actually competing with you, and show where visibility is cheapest to win.
===
name the stores you are up against, and show where visibility is cheapest to win.
>>>
