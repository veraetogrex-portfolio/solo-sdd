---
name: agent-quality
description: Use when measuring or improving the answer quality of an AI agent (support bot, RAG, call scoring, classifier) rather than its code - "collect metrics on the agent", "improve the answer quality", "the agent escalates too often", "run the golden set", "which model is better", "compare the prompts", "check the RAG", "call scoring has drifted" - and before claiming that a prompt, model or retrieval change made the agent better.
---

# agent-quality: agent quality is proven by comparison

An agent is the prompt, the model, retrieval, escalation rules and data together. "It got better" counts only when the new version beat the previous one on the same set of cases and did not make the critical ones worse.

## Order

1. **Version.** Record what is compared: the model, the prompt (a file or a commit), retrieval settings, collections and the data date, escalation rules.
2. **Case set.** Take an existing one: a golden set is the user's labelled table, use it. No set: collect 20-50 real cases from logs, including the critical categories, and show them to the user before the run.
3. **What counts as an answer.** An internal AI note (a draft) is not an answer to the customer: it may not have been used. Only a sent message counts as an answer. Do not mix them.
4. **Metrics** on one set:
   - answer correctness by the labels;
   - escalations: justified, unneeded (not from the allowed categories), missed;
   - grounding: the answer is backed by the retrieved documents;
   - latency and cost per case.
5. **Baseline.** First a run of the current version. Without it the change is not assessed.
6. **Cost before the run.** Before a paid run name: the number of calls, the model, the amount, the stop condition. Preliminary checks run on saved answers and the cheapest models.
7. **Change and a repeated run** on the same set. Change one thing at a time, otherwise it is unclear what worked.
8. **Live check.** Separately look at 5-10 real dialogues after the change: the case set does not cover everything.

## Data

- New scoring rules apply to new records. Recalculating historical data only on a direct request and after describing what changes in the accumulated base.
- Before a conclusion check the schema, the period, the units and what exactly the number means.

## Report (in the user's language)

```
Compared: <version A> → <version B>, set <name, N cases>
Correctness: <A> → <B>
Escalations unneeded / missed: <A> → <B>
Grounding: <A> → <B>
Latency, cost per case: <A> → <B>
Got worse: <cases and categories> | nothing
Calls and amount: plan <…>, actual <…>
Conclusion: accept B | keep A | need more <what>
```

## Mistakes

| Thought | What to do |
|---|---|
| "The answers got better, I looked" | A table of A versus B on one set is needed |
| "I will run 500 cases on a strong model" | First the amount estimate and consent |
| "The AI note matched the labels, so the agent answered right" | Count only sent answers |
| "I will change the prompt, the model and retrieval at once" | One change per run |
| "I will rescore old calls by the new rules" | Only new ones, unless asked otherwise |
| "There are many logs, so there are metrics" | A metric is a number on a labelled set |
