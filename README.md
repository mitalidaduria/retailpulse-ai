
# RetailPulse AI

Retail catalog and inventory intelligence workflow built on **Databricks** and **Delta Lake**, combining semantic product matching, statistical anomaly detection, and **Claude API** summaries over validated outputs.

## Architecture

```mermaid
flowchart LR
  subgraph Sources["Catalog & Inventory Sources"]
    CAT["Catalog Feeds"]
    INV["Inventory Snapshots"]
  end

  subgraph Lakehouse["Databricks & Delta Lake"]
    B["Bronze: Raw Data"]
    S["Silver: Standardized & Validated"]
    G["Gold: Analytical & Feature Tables"]
  end

  subgraph Intelligence["AI & Statistical Checks"]
    EMB["Embeddings: all-MiniLM-L6-v2"]
    VEC["Vector Similarity Search"]
    Z["Z-Score Anomaly Detection"]
    LLM["Claude API Summaries"]
  end

  CAT --> B
  INV --> B
  B --> S --> G
  G --> EMB --> VEC
  G --> Z
  VEC --> LLM
  Z --> LLM
```

## How It Works

* **Catalog & Inventory Sources:** Ingests incoming product catalog feeds and inventory snapshots.
* **Databricks & Delta Lake (`Bronze` → `Silver` → `Gold`):** Preserves raw records in Bronze, standardizes and validates schemas/fields in Silver, and prepares analytical and feature tables in Gold.
* **Semantic Matching & Vector Search:** Generates text embeddings with `all-MiniLM-L6-v2` and runs vector similarity search to surface candidate product matches across catalog variations.
* **Z-Score Anomaly Detection:** Flags unusual numeric observations (such as inventory spikes or drops) relative to baseline distributions.
* **Claude API Summaries:** Generates readable triage summaries from structured/validated outputs rather than inventing metrics directly.

## Repository Structure

```text
retailpulse-ai/
├── README.md
├── docs/
├── src/
└── samples/
```
