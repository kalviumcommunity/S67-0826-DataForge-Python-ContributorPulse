# ContributorPulse Data Cleaning, Validation & Activity Pipeline

The ContributorPulse processing layer cleans, sanitizes, normalizes, and links raw ingested GitHub datasets before feature engineering and KPI calculation.

---

## PRD Traceability Matrix

- **FR-07 (Duplicate Removal):** Identifies and discards duplicate records across users, pull requests, issues, reviews, comments, and commits using primary business keys.
- **FR-08 (Missing-Value Handling):** Imputes missing values with documented, dataset-specific fallbacks (e.g. `(No title)`, `(empty comment)`, `(no commit message)`, clamping negative metrics to 0).
- **FR-09 (UTC Timestamp Standardization):** Standardizes all ingested timestamps to UTC-aware datetime objects (`timezone.utc`) across diverse timezone formats and offsets.
- **FR-10 (Text Normalization):** Cleans text fields (titles, bodies, messages) by stripping leading/trailing whitespace, normalizing Unicode (NFC), and sanitizing null bytes and carriage returns.
- **FR-11 (Contributor ID Validation & Cross-Dataset Linking):** Validates contributor identities, preserves bot contributors (`is_bot=True`), and links contributor activities across pull requests, reviews, comments, issues, and commits.
- **FR-12 (Invalid-Record Quarantine & Error Logging):** Captures invalid, unprocessable records and logs structured error entries into the `ingestion_errors` table with `stage="cleaning_validation"`.
- **FR-13 (Processed Dataset Ready for KPI Calculation):** Persists normalized, validated records in PostgreSQL tables ready for downstream feature engineering and retention KPI calculation.
- **NFR-05 & AC-1:** Guarantees deterministic, idempotent execution without duplicate records or raw data destruction.

---

## Cleaning & Validation Architecture

### 1. Normalization Modules (`backend.app.processing.normalizers`)
- **Text Normalization:** Strips excess whitespace, resolves Unicode formatting (NFC), cleans null bytes/carriage returns, and enforces safe fallback defaults.
- **Timestamp Standardization:** Standardizes string formats, Unix epochs, and non-UTC timezone offsets into UTC-aware datetime objects (`timezone.utc`).

### 2. Dataset-Specific Cleaners (`backend.app.processing.cleaners`)

| Dataset | Cleaning & Validation Rules | Missing Value Strategy |
| :--- | :--- | :--- |
| **Users** | `github_id > 0`, non-empty `login`, bot detection via login patterns (`[bot]`) and `user_type`. | Default `user_type = "User"`, `is_bot = False`. Bot records preserved. |
| **Pull Requests** | `github_id > 0`, `number > 0`, `created_at` timestamp required, metric non-negativity. | Default `title = "(No title)"`, `state = "open"`, `is_merged = True` if `merged_at` present. |
| **Issues** | `github_id > 0`, `number > 0`, `created_at` timestamp required. | Default `title = "(No title)"`, `state = "open"`, `comments_count = 0`. |
| **Reviews** | `github_id > 0`, `submitted_at` required, state normalization to standard enum. | Unknown state defaults to `"COMMENTED"`. |
| **Comments** | `github_id > 0`, `created_at` required, whitespace normalization. | Empty body defaults to `"(empty comment)"`. |
| **Commits** | Valid SHA format regex (`^[0-9a-fA-F]{7,40}$`), additions/deletions clamped to `>= 0`. | Missing message defaults to `"(no commit message)"`, `authored_at` fallback to `committed_at`. |

### 3. Pipeline & Quarantine (`backend.app.processing.pipeline`)
- **Deduplication:** Traverses entities and discards duplicates based on primary business keys (`github_id`, `sha`, `number`).
- **Quarantine Logging:** Invalid or malformed entities are logged to `ingestion_errors` table with `stage="cleaning_validation"`.
- **Processing Statistics:** Computes `input_count`, `output_count`, `duplicate_count`, `invalid_count`, `missing_values_handled_count` across each dataset.
- **Idempotency:** Safe to run repeatedly with deterministic outputs.
