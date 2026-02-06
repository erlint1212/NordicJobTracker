# NordicJobTracker

A robust automated ETL pipeline that scrapes, filters, and organizes job listings from the Norwegian market into an interactive management dashboard. It features intelligent deduplication, AI-driven relevance filtering, and a persistent local database.

## Motivation

Job hunting is often a fragmented process involving repetitive manual searches, loose browser tabs, and disconnected spreadsheets. I found that existing tools didn't offer the granularity I needed—specifically the ability to aggregate niche technical roles (like "DBT Snowflake" or "Systemutvikler") into a single view while automatically filtering out noise.

I built **NordicJobTracker** to solve the "data entry" problem of job searching. By automating the extraction, cleaning, and filtering of job data, I created a system that allows me to focus purely on application quality rather than list management.

## Key Features

* **Smart Deduplication:** Maintains a local SQLite "brain" that remembers every job ever seen. Running a query for "Data Science" won't duplicate a job already found by "Data Engineer."
* **Hybrid Filtering Funnel:**
    * **Layer 1 (Basic):** Instantly rejects roles with irrelevant titles (e.g., "Senior", "Manager") or missing tech keywords.
    * **Layer 2 (AI):** Uses Google Gemini (Flash) to semantically evaluate job descriptions against your specific CV profile, rejecting roles that don't match your experience level.
* **Excel Sync:** A two-way sync system. The script populates an Excel tracker, but also reads your manual status updates (e.g., "Sent Application") back into the database so you never lose progress.
* **Targeted Search:** Ability to run ad-hoc queries without triggering the full scraping pipeline.

## Quick Start

### Prerequisites

* Python 3.10+
* Or a Nix-enabled environment (recommended)
* *(Optional)* A Google Gemini API Key for AI filtering

### Installation

1.  **Clone the repository**

    ```bash
    git clone git@github.com:erlint1212/NordicJobTracker.git
    cd NordicJobTracker
    ```

2.  **Install dependencies**

    ```bash
    pip install -r requirements.txt
    ```

    *(Or run `nix-shell` if you are using Nix)*

3.  **Configure AI (Optional)**
    Set your API key in your environment to enable the AI filter.

    ```bash
    export GEMINI_API_KEY="your_api_key_here"
    ```

4.  **Run the pipeline**

    ```bash
    python main.py
    ```

    The script will initialize the SQLite database, scrape the configured targets, filter candidates, and generate your dashboard in the `/data` folder.

## Usage

### Standard Mode
Runs all queries defined in `config.py` and updates the tracker.

```bash
python main.py

```

### Targeted Search

Scrapes only a specific term. Useful for quick checks without running the full batch.

```bash
python main.py -q "Kubernetes"

```

### Manual Sync

If you have manually updated statuses in the Excel file (e.g., changing a job from "Not searched" to "Applied"), run this to save your changes to the database before the next scrape.

```bash
python main.py --sync

```

### Configuration

The search parameters are fully customizable in `config.py`. You can define priority titles and specific skill combinations:

```python
SEARCH_QUERIES = [
    "Data Engineer",
    "Systemutvikler",
    "Python SQL"
]

```

## The Dashboard (`data/job_application_tracker.xlsx`)

The tool generates a rich Excel file. It is not just a static export; it is a synced dashboard:

* **Status Tracking:** Use the dropdown menu in the "Status" column (e.g., "Sent Application", "1. Interview"). The rows are automatically color-coded based on status.
* **Persistent State:** The script respects your manual inputs. If you mark a job as "Rejected" or "Applied", the scraper will preserve that status in future runs.

## AI Integration

A text file (`output/jobs_for_gemini.txt`) is automatically generated containing full descriptions of only the *new, unsearched* jobs. This file is formatted specifically to be copy-pasted into LLMs (like ChatGPT or Gemini) for quick summarization or cover letter generation.

## Contributing

This project is designed to be modular. If you wish to extend the scraper or add new analytics:

1. **Fork the repository**
2. **Set up your environment:**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dev dependencies
pip install -r requirements.txt

```


3. **Run Tests:** Ensure the database migration logic holds by running the script against a fresh DB instance.
4. **Submit a Pull Request** detailing your changes.

```
