---
name: call-scorecard
description: >-
  Use whenever a market call is made (buy/sell/wait verdict, price level,
  forecast, watchlist add/drop, source endorsement) to log it, and in the weekly
  review or when asked 'how good are your calls?' to grade every call against
  real prices, separate process from luck, and turn misses into skill changes.
---
# Call scorecard: log, grade, learn

Goal: every call is measurable, so the advisor can see whether it adds value and improve (learn, study, adapt, improve). Never invent prices; every grade cites a real close.

## 1. Log every call when it's made
Append one JSON line to the scorecard file (path set by the bot's memory or routine) per call, including on-demand answers, not just briefs:
```
{"id":"2026-11-19-MER-1","date":"YYYY-MM-DD","time":"HH:MM Manila","market":"PSE|US|CRYPTO|BOND|OTHER","ticker":"MER","call":"BUY_PARTS|BUY|WAIT|AVOID|SELL|HOLD|FORECAST","price_at_call":397.8,"entry":[395,380],"wrong_if":370,"trigger":null,"target_or_view":"text","horizon_days":20,"benchmark":"PSEi|SPY|BTC|none","confidence":0.6,"thesis":"one line","sources":["@handle","DragonFi"],"status":"open"}
```
Rules: price_at_call must come from a real quote fetched that day. Every call must carry confidence (0-1); backfilled calls without it are excluded from calibration. Forecasts with scenarios record each scenario's odds. A WAIT call is graded too (did waiting beat buying?).

## 2. Grade (weekly, and when a call's horizon ends or a level hits)
For each open call fetch real daily closes since the call date and record:
- **Fill**: did price reach an entry? (hypothetical fill; real fills only if the user reported them)
- **Wrong-if hit?** and **trigger hit?** with dates.
- **Return**: from hypothetical fill (or price_at_call for BUY) to latest close, and **vs benchmark** over the same days.
- **WAIT/AVOID**: return of the name since the call; a good WAIT is one where the name fell or lagged the benchmark.
- **Max adverse move** (worst drawdown after entry) to judge whether wrong-if levels were sized well.
- **Calibration**: group by confidence bucket; are 60% calls right ~60% of the time?
- Close a call when horizon ends, wrong-if hits, or it's superseded; set status and outcome (WIN/LOSS/SCRATCH, alpha in %).

## 3. Process vs outcome
For each closed call answer: was the thesis right for the right reason? Label one of: good-process/good-outcome, good-process/bad-luck, bad-process/lucky, bad-process/bad-outcome. Only bad-process items produce rule changes; bad luck does not.

## 4. Rolling stats (keep in a summary block / file)
Per market and overall, last 4 weeks and all-time: number of calls, hit rate, average win %, average loss %, expectancy (hit rate x avg win - miss rate x avg loss), alpha vs benchmark, wrong-if hit rate, calibration error, best and worst call. Flag any sample under 20 calls as too small to conclude.

## 5. Source accuracy
Credit or debit each source (X accounts, broker notes, news) cited in a graded call. Combine with the ct-poster-scoring method. Downweight sources whose calls lag the benchmark over 10+ graded calls.

## 6. Learn and adapt
- Write each lesson as a concrete rule change ("PSE: don't buy names during MSCI outflow week before the rebalance date"), not a vibe.
- Apply it as a small, versioned edit to the right skill (playbook, verdict, rebalance, crypto playbook), with a changelog line citing the call ids that justified it.
- Never change a rule on a single loss; need a repeated pattern or a clear process error.
- Record recurring mistakes in a 'known biases' list (e.g. too early on falling knives, levels too tight) and check every new call against it.

## Known biases (check every new call against these; update weekly)
1. Defensive/beta bias: early hits were mostly wait/stay-in-cash calls in a falling market. Report alpha from selection separately from alpha from holding cash. (2026-11-18-PSE-mostly-cash, 2026-11-17-ICT-hold, 2026-11-19-MONDE-nochase, 2026-11-19-AMZN-nochase, 2026-11-19-ANT-skiprule)
2. Rule drift: calls that contradict a written rule (cap breach, two opposite regime rules, call level != file level, dividend buy below the yield floor). Run the pre-publish check. (2026-11-17-CBC-wl, 2026-11-18-PSE-mostly-cash, 2026-11-20-BTC-sitrep, 2026-11-20-JFC-midday)
3. Watch: near-market limits in a downtrend fill and then move against us first (18/18 hypothetical fills in week 1). Not a rule yet.
4. Watch: early fundamental drops that then outperform (2026-11-17-BPI-drop, 2026-11-17-AREIT-drop). Not a rule yet.
5. Missing confidence on calls blocks calibration.

## 7. Report (one screen, plain language)
Tally (calls, hits, misses, open), alpha vs benchmarks, best and worst call, one process lesson, what rule changed, and calibration in one line. If the sample is small, say so plainly.

## Changelog
- v1.1 2026-11-20: known-biases list, mandatory confidence field. From the first weekly grading (57 calls).
