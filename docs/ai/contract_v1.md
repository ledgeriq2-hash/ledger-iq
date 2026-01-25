# AI Contract v1

## Purpose
Ledger IQ only stores externally produced AI results for advisory, read-only, audit-safe reporting. No training or inference happens inside Ledger IQ.

## Ingestion model
Ledger IQ accepts externally produced JSON runs (for example, from Google Colab or cloud pipelines). The system stores and serves these runs without mutation.

## Versioning
- `schema_version` is mandatory and uses semantic versioning (for example, "1.0").
- Any breaking change requires a new major version (for example, "2.0").

## AI run structure
Top-level keys (v1):
- `schema_version` (string)
- `run_meta` (object)
- `payload` (object)

### run_meta (required fields)
- `model_name` (string)
- `model_version` (string)
- `dataset_fingerprint` (string)
- `created_at` (string, ISO 8601 timestamp)
- `created_by` (string, optional)
- `date_from` (string, optional, YYYY-MM-DD)
- `date_to` (string, optional, YYYY-MM-DD)
- `scenario` (string, default "baseline")

### payload
`payload` is an object containing one or more blocks. In v1 the following blocks are allowed and optional:
- `forecast`
- `risk`
- `explainability`
- `insights`

Each block must be a valid JSON object (even if minimal).

## Governance rules
- Runs are immutable after creation.
- Only allowed state changes: revoke (soft) and supersede (link to newer run).
- Revoked runs are never deleted.
- Each run must have `payload_hash` computed via canonical JSON hashing of `payload`.
- An optional `signature` field may be attached for future cryptographic signing. If included in the run document, it should live under `run_meta.signature`.

Note: `payload_hash` is computed on ingestion and stored alongside the run record; it is not part of `payload` in v1.

## Canonical hashing
- Use canonical JSON serialization of `payload` only:
  - sort keys
  - separators without whitespace (`","`, `":"`)
  - UTF-8 encoding
- Hash algorithm: SHA256
- Output: lowercase hex digest (64 characters)
- Hash is computed on `payload` only (not including `run_meta`).
