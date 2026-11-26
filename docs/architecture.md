# RetailPulse AI — Architecture & Design Notes

## 1. System Boundary
- **External Inputs:** Catalog feeds (product metadata, attributes, SKUs/variants) and inventory snapshots (stock levels across time/locations).
- **Lakehouse Layer (`Databricks` & `Delta Lake`):**
  - **Bronze:** Raw ingested records preserved with source context for traceability and replay.
  - **Silver:** Standardized schemas, normalized text/attributes, and validation checks.
  - **Gold:** Curated analytical and feature tables used for downstream checks.
- **Deterministic Intelligence & AI Triage:**
  - **Embeddings (`all-MiniLM-L6-v2`) + Vector Similarity Search:** Surfaces candidate product matches across catalog variations (e.g., evaluating high-similarity candidates such as `>= 0.92` alongside attribute/SKU/brand verification).
  - **Z-Score Anomaly Detection:** Flags numeric observations that deviate sharply from baseline distributions, while accounting for baseline skew, outliers, and seasonality.
  - **Claude API Summaries:** Generates readable triage summaries from validated outputs rather than computing scores or inventing metrics on its own.

## 2. Core Design Rule: Deterministic Checks First, LLM Second
- Deterministic code computes similarity scores, candidate pairs, and anomaly flags from structured data.
- Claude API receives validated findings and produces concise, human-readable summaries for review.
- High semantic similarity is a **candidate signal**, not automatic identity proof attribute, SKU, and variant checks remain essential.
