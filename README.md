# News Crawler

A news crawler supporting Cnyes and EBSCO Newspaper Source, with stock filtering and LLM summarization.

## Data Sources

| Source | Description | Access |
|--------|-------------|--------|
| Cnyes | Taiwan financial news | Public API |
| EBSCO Newspaper Source | International newspapers | NTU VPN required |

## Pipeline

```
1. Crawl          2. Filter           3. Split              4. Analyze          5. Summarize
   Raw News   -->    by Stock    -->    by Trading Day  -->    Distribution  -->    with LLM
```

## Quick Start

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium  # For EBSCO crawler
cp .env.example .env  # Add your API keys
```

## Cnyes News Crawler

```bash
# Crawl Taiwan stock news
python scripts/crawl_news.py --category tw_stock --start 2016-01-01 --end 2025-12-31

# Filter by stock code
python scripts/filter_stocks.py --category tw_stock --start 2016-01-01 --end 2025-12-31 --stock 2330

# Split by trading day
python scripts/split_by_trading_day_v2.py --stock 2330

# Analyze distribution
python scripts/analyze_trading_day.py --stock 2330

# Summarize with LLM
python scripts/summarize_by_llm_v2.py --stock 2330 --start 2025-01-01 --end 2025-12-31
```

## EBSCO News Crawler

Crawl US stock news from EBSCO Newspaper Source (Dow Jones 30 components).

**Requirements:**
- NTU VPN connection (2-hour session limit)
- Playwright browser automation

```bash
# Crawl single stock
python scripts/crawl_ebsco_news.py --stock AAPL --start 2016-01-01 --end 2025-12-31 --headless

# Crawl all 30 Dow Jones stocks
python scripts/crawl_ebsco_news.py --all --start 2016-01-01 --end 2025-12-31 --headless

# Force re-crawl existing stocks
python scripts/crawl_ebsco_news.py --stock AAPL --start 2016-01-01 --end 2025-12-31 --headless --force
```

**Features:**
- Monthly partitioning for large date ranges
- Automatic batch downloading (50 records per batch due to EBSCO limit)
- CSV export with deduplication
- Supports Chinese locale (Taiwan University interface)

**Output:** `data/ebsco_news/{STOCK}.csv`

## Scripts

| Script | Description |
|--------|-------------|
| `crawl_news.py` | Crawl news from Cnyes |
| `crawl_ebsco_news.py` | Crawl news from EBSCO Newspaper Source |
| `filter_stocks.py` | Filter news by stock code |
| `split_by_trading_day.py` | Split by trading window (prev close ~ today open) |
| `split_by_trading_day_v2.py` | Split by trading day (full day 00:00 ~ 23:59) |
| `analyze_trading_day.py` | Generate statistics and distribution chart |
| `summarize_by_llm.py` | Summarize daily news (1-3 paragraphs) |
| `summarize_by_llm_v2.py` | Summarize daily news (one sentence) |

## Data Structure

```
data/
├── raw_tw_stock/                    # Cnyes raw news
│   └── 2024/01/20240102.json
│
├── stocks/
│   ├── tw_stock/                    # Taiwan stocks
│   │   ├── 2330/
│   │   │   └── 201601_202512.json
│   │   ├── analysis/
│   │   ├── by_trading_day/
│   │   └── summaries_v2/
│   │
│   └── us_stock/                    # US stocks
│       └── analysis/
│
└── ebsco_news/                      # EBSCO news
    ├── AAPL.csv
    ├── MSFT.csv
    └── ...
```

## Dow Jones 30 Stocks

The EBSCO crawler supports all 30 Dow Jones Industrial Average components:

```
AAPL, AMGN, AMZN, AXP, BA, CAT, CRM, CSCO, CVX, DIS,
GS, HD, HON, IBM, JNJ, JPM, KO, MCD, MMM, MRK,
MSFT, NKE, NVDA, PG, SHW, TRV, UNH, V, VZ, WMT
```

## Environment Variables

Create `.env` file:
```
OPENAI_API_KEY=your_openai_key
```

## Notes

- **VPN Timeout:** NTU VPN has a 2-hour session limit. For large crawls, you may need multiple sessions.
- **EBSCO Rate:** Each month takes ~5-6 minutes to crawl (~800 records).
- **Full Crawl:** 120 months (2016-2025) for one stock takes ~12 hours.

## License

MIT License
