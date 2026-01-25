# Cnyes News Crawler

A news crawler for cnyes.com with stock filtering and LLM summarization.

## Pipeline

```
1. Crawl          2. Filter           3. Split              4. Analyze          5. Summarize
   Raw News   -->    by Stock    -->    by Trading Day  -->    Distribution  -->    with LLM
   (cnyes)         (2330, NVDA)        (per day JSON)        (chart + stats)       (GPT-4o-mini)
```

## Quick Start

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add your API keys

# Run pipeline
python scripts/crawl_news.py --category tw_stock --start 2024-01-01 --end 2025-12-31
python scripts/filter_stocks.py --category tw_stock --start 2024-01-01 --end 2025-12-31 --stock 2330
python scripts/split_by_trading_day.py --stock 2330 --start 2025-01-01 --end 2025-12-31
python scripts/analyze_trading_day.py --stock 2330
python scripts/summarize_by_llm.py --stock 2330 --start 2025-01-01 --end 2025-12-31
```

## Scripts

| Script | Description |
|--------|-------------|
| `crawl_news.py` | Crawl raw news from cnyes.com |
| `filter_stocks.py` | Filter news by stock code |
| `split_by_trading_day.py` | Split into per-trading-day files |
| `analyze_trading_day.py` | Generate statistics and distribution chart |
| `summarize_by_llm.py` | Summarize daily news with OpenAI |

## Data Structure

```
data/
├── raw_tw_stock/                    # Raw crawled news
│   └── 2024/01/20240102.json
│
└── stocks/tw_stock/2330/            # Filtered stock news
    ├── 202401_202412.json           # All news for date range
    ├── by_trading_day/              # Split by trading day
    │   ├── 2024-01-02.json
    │   └── ...
    ├── summaries/                   # LLM summaries
    │   ├── 2024-01-02.json
    │   └── ...
    └── news_distribution.png        # Analysis chart
```

## Command Reference

### crawl_news.py
```bash
python scripts/crawl_news.py --category tw_stock --start 2024-01-01 --end 2025-12-31
```

### filter_stocks.py
```bash
python scripts/filter_stocks.py --category tw_stock --start 2024-01-01 --end 2025-12-31 --stock 2330
```

### split_by_trading_day.py
```bash
python scripts/split_by_trading_day.py --stock 2330 --start 2025-01-01 --end 2025-12-31
```

### analyze_trading_day.py
```bash
python scripts/analyze_trading_day.py --stock 2330 --threshold 15
```

### summarize_by_llm.py
```bash
python scripts/summarize_by_llm.py --stock 2330 --start 2025-01-01 --end 2025-12-31
python scripts/summarize_by_llm.py --stock 2330 --dry-run  # Preview without API calls
```

## Environment Variables

Create `.env` file (see `.env.example`):
```
FINLAB_API_KEY=your_finlab_key
OPENAI_API_KEY=your_openai_key
```

## License

MIT License
