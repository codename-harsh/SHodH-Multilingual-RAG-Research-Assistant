# Shodh Evaluation

The golden set lives in `golden_dataset/questions.json`.

Each entry requires:

- `id`: stable identifier
- `question`: user question
- `language`: expected query language
- `doc_id`: UUID of an ingested document
- `expected_answer`: reference answer
- `relevant_chunk_ids`: gold evidence chunk IDs

Replace all sample placeholders before running:

```bash
python evaluation/run_eval.py
```

The runner calls the live `/query` endpoint and writes:

- `evaluation/reports/latest.json`
- `evaluation/reports/latest.html`

For meaningful context precision/recall, keep the gold `relevant_chunk_ids` aligned with the chunks actually produced by the current ingestion configuration.
