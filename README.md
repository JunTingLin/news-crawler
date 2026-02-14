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
python scripts/crawl_news.py --category tw_stock --start 2016-01-01 --end 2025-12-31

python scripts/filter_stocks.py --category tw_stock --start 2016-01-01 --end 2025-12-31 --stock 2330

python scripts/split_by_trading_day_v2.py --stock 2330

python scripts/analyze_trading_day.py --stock 2330

python scripts/summarize_by_llm.py --stock 2330 --start 2025-01-01 --end 2025-12-31
```

## Scripts

| Script | Description |
|--------|-------------|
| `crawl_news.py` | Crawl raw news from cnyes.com |
| `filter_stocks.py` | Filter news by stock code |
| `split_by_trading_day.py` | Split by trading window (prev close ~ today open) |
| `split_by_trading_day_v2.py` | Split by trading day (full day 00:00 ~ 23:59) |
| `analyze_trading_day.py` | Generate statistics and distribution chart |
| `summarize_by_llm.py` | Summarize daily news (1-3 paragraphs) |
| `summarize_by_llm_v2.py` | Summarize daily news (one sentence) |

### Batch Scripts (TWII 29 Stocks)

| Script | Description |
|--------|-------------|
| `batch_filter_stocks.sh` | Filter all 29 TWII component stocks |
| `batch_split_trading_day_v2.sh` | Split all 29 stocks by trading day |

## Data Structure

```
data/
├── raw_tw_stock/                    # Raw crawled news
│   └── 2024/01/20240102.json
│
└── stocks/tw_stock/
    ├── 1216/                        # Filtered stock news
    │   └── 201601_202512.json
    ├── 2330/
    │   ├── 201601_202512.json
    │   └── news_distribution.png    # Analysis chart
    ├── by_trading_day/              # Split by trading day
    │   ├── 1216/
    │   │   ├── 2024-01-02.json
    │   │   └── ...
    │   └── 2330/
    │       └── ...
    ├── summaries/                   # LLM summaries (1-3 paragraphs)
    │   ├── 1216/
    │   │   ├── 2024-01-02.json
    │   │   └── ...
    │   └── 2330/
    │       └── ...
    └── summaries_v2/                # LLM summaries (one sentence)
        ├── 1216/
        │   ├── 2024-01-02.json
        │   └── ...
        └── 2330/
            └── ...
```

## Command Reference

### crawl_news.py
```bash
python scripts/crawl_news.py --category tw_stock --start 2016-01-01 --end 2025-12-31
```

### filter_stocks.py
```bash
python scripts/filter_stocks.py --category tw_stock --start 2016-01-01 --end 2025-12-31 --stock 2330
```

### split_by_trading_day.py (prev close ~ today open)
```bash
python scripts/split_by_trading_day.py --stock 2330
```

### split_by_trading_day_v2.py (full day)
```bash
# Taiwan stocks (uses ^TWII)
python scripts/split_by_trading_day_v2.py --stock 2330

# US stocks (uses ^DJIA)
python scripts/split_by_trading_day_v2.py --stock AAPL --category us_stock

# Custom index
python scripts/split_by_trading_day_v2.py --stock 2330 --index ^TWII
```

### analyze_trading_day.py
```bash
python scripts/analyze_trading_day.py --stock 2330 --threshold 15
```

### summarize_by_llm.py (1-3 paragraphs)
```bash
python scripts/summarize_by_llm.py --stock 2330 --start 2025-01-01 --end 2025-12-31
python scripts/summarize_by_llm.py --stock 2330 --dry-run  # Preview without API calls
```

### summarize_by_llm_v2.py (one sentence)
```bash
python scripts/summarize_by_llm_v2.py --stock 2330 --start 2025-01-01 --end 2025-12-31
python scripts/summarize_by_llm_v2.py --stock 2330 --dry-run
```

## Environment Variables

Create `.env` file (see `.env.example`):
```
OPENAI_API_KEY=your_openai_key
```

## License

MIT License
