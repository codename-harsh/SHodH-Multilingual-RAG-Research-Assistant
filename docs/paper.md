# Benchmarking Multilingual Retrieval Quality in RAG Systems: A Cross-Linguational Analysis

## Abstract

This paper evaluates Shodh, a multilingual retrieval-augmented generation system combining multilingual dense embeddings, BM25 sparse retrieval, score fusion, local cross-encoder reranking, and citation-constrained generation. The evaluation measures faithfulness, answer relevancy, context precision, and context recall across languages. Results are generated directly from the project's golden dataset so that reported values remain coupled to the evaluated system configuration.

## 1. Introduction

Retrieval-augmented generation can reduce unsupported generation by grounding language models in an external document corpus. Multilingual systems add a second challenge: retrieval quality must remain useful when the language of a query differs from the language or vocabulary distribution of the source material. Shodh addresses this with multilingual embeddings and a hybrid dense/sparse retrieval stage.

## 2. Methodology

### 2.1 System

Documents are parsed page-by-page with PyMuPDF and split into approximately 512-token chunks with 128-token overlap. Each chunk receives a multilingual dense embedding from Cohere and a BM25 sparse representation stored in Qdrant. For a query, the system retrieves 20 dense and 20 sparse candidates, normalizes their scores, and combines them using a configurable dense weight of 0.7. The fused candidates are reranked with `cross-encoder/ms-marco-MiniLM-L-6-v2`; four chunks are passed to Gemini under a grounding prompt requiring page and chunk citations.

### 2.2 Dataset

The project includes a 15-entry starter golden dataset covering English and Hindi queries. Each entry records the expected answer and relevant chunk IDs. The dataset is intentionally editable so additional documents and languages can be added without changing the evaluation runner.

### 2.3 Metrics

RAGAS is used to measure faithfulness, answer relevancy, context precision, and context recall. Results are grouped by query language and document type.

## 3. Results

The following section is populated from `evaluation/reports/latest.json` after an evaluation run. No synthetic scores are inserted into the paper.

| Language | Faithfulness | Answer relevancy | Context precision | Context recall |
|---|---:|---:|---:|---:|
| Generated from evaluation | — | — | — | — |

### 3.1 Ablation

The planned ablation compares the configured hybrid retriever against a dense-only baseline using the same reranking and generation stages. The baseline implementation should be run against the same golden set before publication.

## 4. Discussion

Hybrid retrieval is intended to combine semantic matching with exact-term sensitivity. Cross-encoder reranking further narrows the final evidence set. Multilingual embeddings allow query and document representations to share a semantic space, while language detection affects answer language and optional retrieval filtering rather than changing the fundamental pipeline.

The evaluation should be interpreted with the size and composition of the golden set in mind. A 15-entry starter set is useful for engineering feedback but is not a sufficient basis for broad claims about multilingual RAG quality.

## 5. Conclusion

Shodh provides an inspectable multilingual RAG pipeline in which ingestion, retrieval, reranking, generation, and evaluation are separately testable. The final paper should replace the results placeholders with the output of the current golden dataset and report the dense-only ablation before submission.

## References

1. PyMuPDF documentation.
2. Qdrant documentation.
3. Cohere Embed Multilingual documentation.
4. RAGAS documentation and paper.
5. Sentence Transformers documentation.
