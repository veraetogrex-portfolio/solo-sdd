---
name: evidence-research
description: Use when the user asks to compare options, research a market or tool, or pick a solution under constraints - "compare", "do research", "research", "deep research", "what to choose", "find a solution for", "which bank did this", "are they alive", "find links and back them up in a table", "find the best settings" - whether the subject is tech, banking, pricing, a purchase or a trip.
---

# evidence-research: a choice on checked facts

The result is a recommendation you can use right away: the options fit the user's constraints, every fact has a source and a date. General reasoning ("many banks adopt AI") is not a result.

## Order

1. **Criteria.** From the request and the context write out the constraints: budget, city, deadlines, stack, jurisdiction, "free", the number of options. Decide what is missing yourself and note it in the report, do not ask.
2. **Search.** Primary sources: the product site, documentation, pricing, official news, registries. Reviews and aggregators only as a hint where to look.
3. **Specifics.** A named product, company, model, feature, price, address, time. "Bank X launched Y in <month, year>", not "banks use".
4. **Freshness.** For a price, availability, a schedule and "is the project alive", the check date. Signs of life: the last release or news, activity, whether the site works.
5. **Filtering.** An option that violates a constraint does not get into the table. It can be mentioned in one line, why it was dropped.
6. **Comparison** in a table by the criteria from step 1. The source link goes in the row, not in a list at the end.
7. **Recommendation.** One option and why. Alternatives if a choice was asked for or if the leader depends on a condition.
8. **Unknowns.** What could not be confirmed and what can only be checked in person.

**No internet.** First use the available official documents, cache and history; give the date of the source itself. For a price, availability, a schedule and activity mark "freshness unknown"; do not pass off an old price or activity as current. Do the rest of the analysis on the available data, make the recommendation conditional: what to choose if the unconfirmed conditions hold. Do not stop the whole task for lack of network and do not demand actions from the user while there are available sources and useful conclusions.

## Answer form

```
Criteria: <list; decisions made without you>
<table: option | key parameters | price/availability on the date | source>
Recommendation: <option> — <why, 1-2 sentences>
Not confirmed: <facts without a source or needing a personal check>
```

Size fits the task: for an everyday question a table of 3-5 rows, for work research as requested. Create a document only if asked.

## Mistakes

| Thought | What to do |
|---|---|
| "I will describe the market trends" | Named players and their features are needed |
| "The price was this last year" | Check it for today or mark it unchecked |
| "The platform is on the list, so it fits" | Check whether it is alive and popular |
| "I will give 10 options to choose from" | As many as asked; by default the single best one |
| "I will attach the sources at the end" | The source next to the fact |
| "It will surely work" | Separate what is checked from what must be tried in person |
