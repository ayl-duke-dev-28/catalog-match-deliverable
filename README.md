# Catalog Match

A local single-page web app for matching free-form customer product requests to the top 3 likely catalog entries. The stretch challenge is included: selecting a customer folds prior order history into the ranking.

## What It Does

- Accepts natural-language product descriptions such as `M8 x 50mm BHCS` or `1/4-20 x 3/4 hex cap screw zinc`.
- Returns the top 3 active catalog matches with confidence scores and short scoring reasons.
- Provides a searchable customer dropdown. When selected, the matcher uses that customer's order history as a personalization signal.
- Runs fully locally. No API key, external service, or third-party Python package is required.

## Easiest Run: Docker

This is the most portable way to demo the project on another computer because Docker supplies Python and dependencies.

1. Install Docker Desktop.
2. Download this folder or unzip `catalog-match-deliverable.zip`.
3. In the project folder, run:

```bash
docker compose up --build
```

Open `http://127.0.0.1:8000`.

## Run Without Docker

Mac/Linux:

```bash
./scripts/start.sh
```

Windows:

```bat
scripts\start.bat
```

Manual Python setup:

```bash
python3 app.py
```

Then open `http://127.0.0.1:8000`.

## Project Structure

- `app.py` serves the static UI and JSON endpoints using Python's standard library HTTP server.
- `catalog_match/data.py` loads the tab-delimited catalog and order-history CSVs.
- `catalog_match/matcher.py` contains normalization, attribute extraction, ranking, confidence scoring, and personalization.
- `static/` contains the single-page UI.
- `DECISIONS.md` explains the approach, tradeoffs, and edge cases.

## API

- `GET /api/customers`
- `POST /api/match` with JSON:

```json
{
  "query": "M8 x 50mm BHCS",
  "customer_id": "CUST-001"
}
```

- `GET /api/health`

## Smoke Test

With a server running:

```bash
python3 scripts/smoke_test.py
```

The script checks the health endpoint and runs a few representative queries.
