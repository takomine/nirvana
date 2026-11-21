---
name: ph-advisor-self-review
description: >-
  Use for the weekly (Friday after close) review of the PH advisor, or whenever
  a call went clearly right or wrong. It covers grading past verdicts against
  outcomes, extracting lessons, checking that the skills load, and updating the
  other ph-* skills with versioned changelogs.
---
# PH advisor self-review (keeps the skill set improving)

Covers the skill set: `ph-market-playbook`, `ph-stock-market-research`, `ph-stock-verdict`, `plain-language-market-brief`, `ph-trade-journal`, and this file.

## 1. Health check (do first)
- [ ] Load each skill above with the Skill tool. List any that **fail to load** and report them to the user so they can be restored. Use the last good draft or memory meanwhile.
- [ ] Re-test the endpoints in `ph-stock-market-research` §2 (phisix, DragonFi v2). Note any change.
- [ ] Check routines ran (pre-market brief, Before the Bell add-on). Note missed or late runs.

## 2. Grade the week's calls
Pull every verdict logged this week (`ph-trade-journal`). For each, fetch the latest close.
| Label | Graded ✅ if | ❌ if |
|---|---|---|
| Buy / Buy in parts | Close ≥ entry or limit, and wrong-if not hit | Closed below wrong-if |
| Wait for ₱X | It reached ₱X (good patience) or kept falling | It ran >5% higher without touching ₱X (missed) |
| Avoid | It fell or went nowhere | It rose >5% on its thesis-relevant news |
- Also grade **process**, separate from outcome: price fresh? sources cited? dividend status right? fees and lots right? plain language? A good process with a bad outcome isn't a lesson to over-learn.
- Mark too-early calls (<5 trading days old) as "open", not graded.
- Tally: hits / misses / open / ungradeable, and the process errors found.

## 3. Extract lessons
For each miss or process error, write one line:
`YYYY-MM-DD: <what happened>. Rule: <the specific change>. → <skill §section>`
- A lesson must change behavior (a checklist item, a threshold, a source tier). Otherwise drop it.
- Require 2+ occurrences before changing a scoring threshold. One-off events go in the lessons log only.
- Never "learn" a fact that isn't verified. Mark it [U] in the playbook instead.

## 4. Update the skills (exact procedure)
1. Edit only the section the lesson points to. Keep each skill **≤150 lines**. Merge or trim stale rows rather than appending forever.
2. Facts and calendar → `ph-market-playbook` (move past calendar rows out; add the next 4–6 weeks with [V]/[U] tags).
3. Source or endpoint changes → `ph-stock-market-research`.
4. Decision rule changes → `ph-stock-verdict`.
5. Wording issues the user reacted to → `plain-language-market-brief`.
6. Add the lesson line to playbook §9 (newest first; keep the last ~15 and archive older ones in memory).
7. Bump the version in each touched file's **Changelog** at the bottom: `- vN YYYY-MM-DD: <what changed, why (lesson ref)>`.
8. No user-specific data (names, budgets, positions) in skills. Those go in memory.
9. Save with the skill-saving tool. If you can't save, draft the files and ask the parent or user to save them.

## 5. Report to the user (one phone screen, plain language)
```
**Week of <dates>: <hits>/<graded> calls worked.**
- Best call: … | Worst call: … (why)
- What I'm changing: 1–3 bullets
- Skills: all loaded ✅ / <name> missing ⚠️
- Next week's big dates: …
```

## 6. Guardrails
- Don't rewrite whole skills in one review. Make small, traceable edits.
- Don't hide misses. Report them first.
- If outcomes are random over a week, say so. Judge the framework over a month or more.

## Changelog
- v1 2026-11-13: new. Health check, grading table, process vs outcome, lesson format, update procedure with versioned changelogs, report template.
