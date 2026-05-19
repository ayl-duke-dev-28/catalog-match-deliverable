# Catalog Match Decisions

## Matching Approach

I used a deterministic local matcher instead of an LLM or embedding service. The catalog is small enough that scanning all active rows is fast, and a local approach is easier to demo, explain, and ship without API keys or package installation.

The matcher combines:

1. **Text similarity:** TF-IDF cosine similarity over normalized tokens, bigrams, and trigrams.
2. **Fastener-specific normalization:** common shorthand is expanded before scoring, for example `SHCS` to `socket head cap screw`, `BHCS` to `button socket cap screw`, `HX` to `hex`, `SCR` to `screw`, `WSHR` to `washer`, and `ZN` to `zinc`.
3. **Attribute extraction:** product type, diameter, thread, length, material, and finish are extracted with regular expressions and receive explicit boosts or penalties.
4. **Confidence:** the displayed confidence is the final blended score on a 1-99 scale. It is intentionally not a probability; it is a calibrated ranking score that rises when the query text, extracted attributes, and customer history agree.

This hybrid approach is more defensible than plain keyword search because it can distinguish a query like `M8 x 50mm BHCS` from other M8 screws, while still handling catalog shorthand and inconsistent casing.

## Stretch Challenge: Personalization

When a customer is selected, the app builds a lightweight profile from order history:

- previously purchased SKUs
- frequent product types
- frequent diameters and threads
- common materials and finishes

Each order is weighted by recency and quantity. A direct prior SKU purchase is the strongest personalization signal, followed by product type, size, and material/finish similarity.

The final score blends description relevance and history relevance. History has a small weight for specific queries and a larger weight for vague or reorder-style queries containing words like `same`, `last`, or `again`. This keeps a precise request from being overruled by history, but lets a query like `the same washers as last time` lean heavily on customer behavior.

## Edge Cases Considered

- **Abbreviations and shorthand:** handled with phrase expansion before tokenization.
- **Missing attributes:** if the user says `1/2 inch hex nut`, the matcher can still use the `1/2` diameter even when thread pitch is missing.
- **Conflicting attributes:** mismatched explicit type, diameter, thread, or length receives a penalty so close-but-wrong items fall lower.
- **Vague requests:** broad queries produce lower confidence because fewer explicit attributes are available.
- **New customers:** if no customer is selected, or an unknown customer id is sent, the matcher uses description-only scoring.
- **History conflicts:** personalization is blended after base relevance, so prior purchases nudge results but do not dominate highly specific product descriptions.
- **Dirty CSV header:** `catalog.csv` contains a stray terminal control sequence before `catalog_id`; the data loader strips control characters from headers instead of editing source data.

## Alternatives Considered

- **LLM-only matching:** flexible, but harder to explain, slower, and dependent on an external key.
- **Embeddings-only matching:** good for semantic similarity, but can underweight exact mechanical attributes like `5/16-18` or `2-1/2`.
- **Pure keyword matching:** simple, but brittle with abbreviations like `SHCS`, `BHCS`, `HX`, and `WSHR`.

The chosen hybrid matcher keeps exact fastener attributes visible while still being tolerant of natural customer wording. I also used Python's standard-library HTTP server instead of a web framework so the submitted zip runs anywhere Python 3 is installed.
