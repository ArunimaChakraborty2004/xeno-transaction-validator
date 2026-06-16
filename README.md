# Xeno Transaction Validator

A production-ready MVP web platform for **transaction data validation and processing**, built with Python and Streamlit. Upload CSV files, run automated validation, review a dashboard-style report, and download cleaned or invalid record exports.

Deploy directly to [Streamlit Cloud](https://streamlit.io/cloud) with zero configuration changes.

---

## Features

| Feature | Description |
|---------|-------------|
| **CSV Upload** | Upload order-level, product-level, and payment transaction data |
| **Data Preview** | Preview uploaded data with row and column counts |
| **Validation Engine** | Phone, date, payment mode, and data quality checks |
| **Validation Report** | Dashboard metrics with error breakdown by category |
| **Cleaned Output** | Adds `validation_status` and `validation_errors` columns |
| **Download Center** | Export cleaned CSV, invalid records, and summary report |
| **CSV Chunking** | Auto-split datasets > 100 rows into downloadable parts |
| **AI Data Insights** | Auto-generated payment, duplicate, missing data, and failure insights |
| **Visual Analytics** | Altair charts for payment, country, and validation status |
| **Data Quality Score** | Composite 0–100 score with quality tier label |
| **Executive Summary** | Human-readable stakeholder narrative |
| **Client-facing UI** | Branded SaaS layout with insight cards and chart panels |

---

## AI Insights & Analytics

After validation, the platform automatically generates:

- **Data Quality Score** (0–100) weighted by pass rate, completeness, and uniqueness
- **Executive Summary** — e.g. *"This dataset contains 523 records. 487 records passed validation..."*
- **Insight cards** — dominant payment mode, duplicate count, missing data %, top failure
- **Charts** — payment mode distribution, country distribution, validation status breakdown

Insights logic lives in `insights.py` (rule-based analytics, no external API required).

---

## Validation Rules

### Phone numbers
Configurable per country via `config.py`:

| Country | Digits |
|---------|--------|
| India | 10 |
| Singapore | 8 |
| United States | 10 |
| United Kingdom | 10 |

Add new countries by extending `PHONE_COUNTRY_RULES`.

### Dates
Supported formats:
- `YYYY-MM-DD`
- `DD-MM-YYYY`
- `DD/MM/YYYY`
- (and more — see `config.py`)

### Payment modes
Allowed values: **UPI**, **Card**, **Cash**, **Net Banking**, **Wallet**

### Data quality
- Missing values
- Duplicate rows
- Invalid email (when email column is detected)
- Invalid numeric fields (amount, quantity, price, etc.)
- Empty records

---

## Project Structure

```
project/
├── app.py              # Streamlit UI entry point
├── validator.py        # Core validation engine
├── insights.py         # AI insights, scoring, executive summary
├── config.py           # Rules, constants, column heuristics
├── utils.py            # CSV I/O, chunking, helpers
├── requirements.txt    # Python dependencies
├── README.md
└── sample_data/
    ├── sample_transactions.csv
    └── sample_large_transactions.csv
```

---

## Quick Start (Local)

### Prerequisites
- Python 3.9+

### Installation

```bash
cd "Xeno Assign"
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Run the app

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

### Try sample data

Upload `sample_data/sample_transactions.csv` to see validation in action. The sample includes valid rows, invalid phones, bad dates, unknown payment modes, duplicates, empty records, and invalid numeric values.

---

## Streamlit Cloud Deployment

1. Push this repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io).
3. Click **New app** → connect your repo.
4. Set **Main file path** to `app.py`.
5. Deploy.

Streamlit Cloud installs dependencies from `requirements.txt` automatically.

---

## Output Columns

After validation, two columns are appended to your dataset:

| Column | Example values |
|--------|----------------|
| `validation_status` | `Valid`, `Invalid` |
| `validation_errors` | `Invalid Phone; Invalid Date`, *(empty if valid)* |

---

## Extending the Validator

### Add a country phone rule

Edit `config.py`:

```python
PHONE_COUNTRY_RULES["Australia"] = {
    "code": "AU",
    "digits": 9,
    "description": "9-digit phone number",
}
```

### Add a payment mode

```python
ALLOWED_PAYMENT_MODES.append("BNPL")
# Rebuild lookup (or restart app — lookup is built at import)
```

### Customize chunk size

```python
CHUNK_SIZE = 200  # default is 100
```

---

## License

MIT — use freely for demos, assignments, and production pilots.

---

Built with ❤️ for reliable transaction data pipelines.
