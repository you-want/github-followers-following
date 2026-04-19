# GitHub Followers Following Analyzer

A robust and concurrent tool to analyze relationships between GitHub followers and following lists.

Built with asynchronous Python (`aiohttp` + `asyncio`) to ensure ultra-fast data fetching, while using SQLite for local persistence to enable smart, incremental updates.

## Key Features

- **Blazing Fast Concurrent API Fetching**: Uses asynchronous requests to concurrently fetch both followers and following lists, automatically handling GitHub's pagination and rate limiting.
- **Robust Storage & Caching**: Persists raw JSON data to local storage and updates relationships inside a local SQLite database, avoiding duplicate fetches and allowing for historical analysis.
- **Smart Relationship Engine**: 
  - Detects **mutual** followers (you follow them, they follow you).
  - Detects **one-way** relationships (e.g. people who don't follow you back).
  - Computes the **union** of both lists with `is_following_back` markers.
- **Interactive Web UI & Charts**: Added a beautiful `Streamlit` based UI that provides a dashboard with data tables, metrics, and Plotly pie charts out-of-the-box.
- **Rich CLI & Reporting**: Beautiful terminal output powered by `rich`, with options to export results as CSV, JSON, or an HTML report.

## Directory Structure
```
github-followers-following/
├── src/                # Core implementation
│   ├── analyzer.py     # Relationship analysis engine
│   ├── api.py          # GitHub Async API client
│   ├── config.py       # Configuration and Logging
│   └── storage.py      # SQLite Storage engine
├── tests/              # Pytest unit tests
├── data/               # Persistent storage (Raw JSON & SQLite DB)
├── logs/               # Application logs
├── scripts/            # Shell scripts (e.g., tests runner)
├── main.py             # CLI Entry point
└── ...
```

## Quick Start

### 1. Prerequisites
- Python 3.9+
- Docker and Docker Compose (Optional)

### 2. Configuration

Create your `.env` file from the example:
```bash
cp .env.example .env
```
Provide your GitHub Personal Access Token in `.env` for higher rate limits (5000 requests/hour vs 60 requests/hour). 

#### How to get a GitHub Token?
1. Go to your GitHub [Personal Access Tokens (classic) settings](https://github.com/settings/tokens).
2. Click **Generate new token** -> **Generate new token (classic)**.
3. Add a note (e.g., "Followers Analyzer") and select **No expiration** (or your preferred duration).
4. Under scopes, you don't need to select any special permissions (public data is enough), but checking `read:user` is recommended.
5. Click **Generate token** and copy the resulting string (starts with `ghp_`).

*Note: If you have the GitHub CLI (`gh`) authenticated, the script will try to automatically extract the token from `~/.config/gh/hosts.yml`.*

### 3. Running Locally

**Install Dependencies:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Option A: Web UI (Recommended)
You can start the interactive dashboard with charts and tables using Streamlit:
```bash
streamlit run app.py
```
This will automatically open `http://localhost:8501` in your browser.

#### Option B: CLI Mode
**Run Analysis:**
```bash
# See all mutuals as a rich terminal table
python main.py --user torvalds --action mutual

# Export one-way following (people you follow but don't follow you back) to CSV
python main.py --user defunkt --action one-way --output csv

# Export union of all relationships to an HTML report
python main.py --user mojombo --action union --output html
```

*Available Actions:* `followers`, `following`, `mutual`, `one-way`, `union`
*Available Outputs:* `table`, `csv`, `json`, `html`

### 4. Running with Docker Compose

If you prefer an isolated environment:
```bash
# This will build the image and run the default command
docker compose up --build
```
You can override the default command in `docker-compose.yml` to specify the user and action you want to analyze.

## Tests and Formatting

We use `pytest` for unit testing with a target of ≥80% coverage, alongside `black`, `isort`, and `flake8` for formatting.

```bash
# Run the test suite and formatters
chmod +x scripts/run_tests.sh
./scripts/run_tests.sh
```
