# Company RAG — Privacy Notice & GDPR Notes

This document describes how the `company-rag` system processes personal data
from `src/rag/dataset/`. It is a **technical transparency note** for developers
and demo operators — it is **not** legal advice.

## Processing purpose

| Purpose | Description | Lawful basis (demo assumption) |
|---------|-------------|-------------------------------|
| `hr_policy` | Answer questions about company HR policy PDF | Legitimate interest (internal knowledge) |
| `hr_analytics` | Workforce / org structure queries | Legitimate interest (employment admin) |
| `hr_admin` | Individual compensation band lookups | Employment / HR admin (restricted role) |

## Categories of data

- **Policy text** (non-personal): remote work, leave, probation, dress code, etc.
- **Workforce data** (personal): employee IDs, department, location, seniority,
  work mode, promotion history, salary **bands**, org reporting lines.
- **Direct identifiers** (`name`, and by default `gender` / `age` in embedded
  text) are **pseudonymized or excluded** at ingest when `GDPR_PSEUDONYMIZE=true`.

## Privacy by design controls

1. **Pseudonymization** — `Employee-{hmac}` tokens in embedded text; `subject_id`
   kept only in Qdrant payload for erasure/export filters.
2. **Data minimization** — `GDPR_SENSITIVITY=high` drops demographics and keeps
   salary bands only; `GDPR_EXCLUDE_FIELDS` can drop additional columns.
3. **Local processing** — Ollama and Qdrant run locally; no cloud LLM/embedding APIs.
4. **Access roles** — `employee` (default), `hr_admin`, `dpo` with CLI enforcement.
5. **Audit** — append-only JSONL at `GDPR_AUDIT_LOG_PATH` (question hashes by default).
6. **Retention** — `company-rag purge-expired` removes vectors older than
   `GDPR_RETENTION_DAYS`.
7. **Erasure / access** — `company-rag erase` / `export` by `employee_id`.

## Data flows

```
CSV/PDF (source of record)
  → Tabular/PDF loader + Pseudonymizer
  → Chunks + metadata (lawful_basis, purpose, ingested_at)
  → Ollama embeddings (localhost)
  → Qdrant (127.0.0.1)

Query
  → Audit log (hashed question)
  → Role check / refusal
  → Retrieve → Ollama LLM → response redactor
```

## DPIA checklist (demo)

| Question | Status |
|----------|--------|
| Is processing necessary for the stated purpose? | Document yes/no before production use |
| Are direct identifiers minimized? | Yes by default (`GDPR_PSEUDONYMIZE=true`) |
| Can subjects request access/erasure? | Yes via CLI (`export` / `erase`) |
| Is retention limited? | Yes (`GDPR_RETENTION_DAYS` + purge) |
| Are processors documented? | Local only; no subprocessors if Ollama+Qdrant stay on-prem |
| Is Qdrant network-exposed? | Compose binds to localhost only |
| Salt rotated / secrets managed? | **You must** set a strong `GDPR_PSEUDONYM_SALT` |

## Operator obligations

- Replace `GDPR_PSEUDONYM_SALT` before any real data use.
- Do not enable `GDPR_QUERY_LOG_PII=true` unless justified and secured.
- Treat source CSVs as the authoritative store; erasure from Qdrant does **not**
  delete the CSV — remove or anonymize source files separately if required.
- This synthetic dataset is for demo/training only.
