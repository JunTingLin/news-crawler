# Cnyes News Crawler

A robust news crawler for cnyes.com with resume capability and stock filtering.

## Features

- ✅ **Resume capability** - Automatically skip already crawled dates
- ✅ **Stock filtering** - Filter by stock codes
- ✅ **Multi-category** - Support Taiwan stocks (tw_stock) and US stocks (us_stock)
- ✅ **Organized storage** - Data stored in `YYYY/MM/YYYYMMDD.json` structure
- ✅ **Date range support** - From 2015 onwards (370K+ articles)
- ✅ **No API key required** - Uses free Media API

## Quick Start

### 1. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### 2. Crawl Raw News Data

```bash
# Crawl Taiwan stock news (2015-2025)
python scripts/crawl_news.py --category tw_stock --start 2015 --end 2025

# Crawl US stock news (2024-2025)
python scripts/crawl_news.py --category us_stock --start 2024 --end 2025

```

**Resume capability**: If interrupted, simply run the same command again. It will automatically skip already crawled months.

### 3. Filter Stock News

```bash
# Filter Taiwan stocks from raw data
python scripts/filter_stocks.py --category tw_stock \
    --start 2024-01-01 --end 2024-12-31

# Filter specific stocks only
python scripts/filter_stocks.py --category tw_stock \
    --start 2024-01-01 --end 2024-12-31 \
    --stock 2330 2454

# Filter US stocks
python scripts/filter_stocks.py --category us_stock \
    --start 2024-01-01 --end 2024-12-31 \
    --stock NVDA TSLA
```

### 4. Split by Trading Day (Secondary Filter)

```bash
# Split stock news by trading day
# Each file contains news from previous close (13:30) to current open (09:00)
python scripts/split_by_trading_day.py --stock 2330

# Specify date range
python scripts/split_by_trading_day.py --stock 2330 \
    --start 2024-01-01 --end 2024-12-31
```

**Requires**: finlab SDK (for Taiwan stock trading calendar)

## Project Structure

```
news-crawler/
├── cnyes_crawler.py               # Core crawler library
├── requirements.txt               # Python dependencies
├── README.md                      # This file
│
├── scripts/                       # Executable scripts
│   ├── crawl_news.py             # Crawl raw news with resume
│   ├── filter_stocks.py          # Filter stocks from raw data
│   └── split_by_trading_day.py   # Split news by trading day
│
├── docs/                          # Documentation
│   └── API_REFERENCE.md          # API reference and categories
│
└── data/                          # Data directory (auto-created)
    ├── raw_tw_stock/              # Taiwan stock raw news
    │   └── 2024/
    │       └── 12/
    │           ├── 20241201.json
    │           ├── 20241202.json
    │           └── ...
    │
    ├── raw_us_stock/              # US stock raw news
    │   └── 2024/
    │       └── ...
    │
    └── stocks/                    # Filtered stock news
        ├── tw_stock/
        │   ├── 2330/
        │   │   ├── 202401_202412.json
        │   │   └── by_trading_day/     # Secondary filter output
        │   │       ├── 2024-01-02.json
        │   │       ├── 2024-01-03.json
        │   │       └── ...
        │   ├── 2454/
        │   └── ...
        └── us_stock/
            ├── NVDA/
            └── ...
```

## Stock Lists

### Taiwan Stocks (16 stocks)

```python
# Format: "stock_code": [list of keywords to search]
TWII_STOCKS = {
    "1301": ["1301"],
    "1303": ["1303"],
    "2002": ["2002"],
    "2308": ["2308"],
    "2317": ["2317"],
    "2330": ["2330"],
    "2412": ["2412"],
    "2454": ["2454"],
    "2881": ["2881"],
    "2882": ["2882"],
    "2891": ["2891"],
    "5880": ["5880"],
    "3008": ["3008"],
    "3045": ["3045"],
    "3711": ["3711"],
    "6505": ["6505"],
}
```

**Note**: When using multiple keywords, ALL keywords must appear in the news (AND logic). For example, `"1216": ["1216", "統一"]` will only match news containing BOTH "1216" AND "統一", avoiding false positives like "營收1216.84億元"

### US Stocks (7 stocks, extendable)

```python
# Format: "stock_code": [list of keywords to search]
US_STOCKS = {
    "NVDA": ["NVDA"],
    "TSLA": ["TSLA"],
    "AAPL": ["AAPL"],
    "MSFT": ["MSFT"],
    "GOOGL": ["GOOGL"],
    "META": ["META"],
    "AMZN": ["AMZN"],
}
```

## Usage Examples

### Example 1: Build Complete Database (2015-2025)

```bash
# Step 1: Crawl all Taiwan stock news
python scripts/crawl_news.py --category tw_stock --start 2015 --end 2025

# This will take ~2-3 hours and create:
# - ~22,848 articles (11 years)
# - ~45 MB storage
# - Files in data/raw_tw_stock/YYYY/MM/YYYYMMDD.json

# Step 2: Filter stocks from raw data
python scripts/filter_stocks.py --category tw_stock \
    --start 2015-01-01 --end 2025-12-31

# This creates filtered news for each stock in data/stocks/tw_stock/
```

### Example 2: Resume from Interruption

```bash
# If crawling was interrupted at 2020/06:
python scripts/crawl_news.py --category tw_stock --start 2015 --end 2025

# Output:
# Found 50 months to crawl (missing months only)
# Will skip 2015/01 ~ 2020/05 (already exists)
# Will crawl 2020/06 ~ 2025/12
```

### Example 3: Update Latest News

```bash
# Crawl only recent months
python scripts/crawl_news.py --category tw_stock \
    --start 2025 --end 2025

# Filter recent news
python scripts/filter_stocks.py --category tw_stock \
    --start 2025-01-01 --end 2025-12-31
```

### Example 4: Analyze Specific Stocks

```bash
# Only filter TSMC and MediaTek
python scripts/filter_stocks.py --category tw_stock \
    --start 2024-01-01 --end 2024-12-31 \
    --stock 2330 2454

# Results saved to:
# - data/stocks/tw_stock/2330/202401_202412.json
# - data/stocks/tw_stock/2454/202401_202412.json
```

## Data Storage

### Raw News Storage

- **Location**: `data/raw_{category}/YYYY/MM/YYYYMMDD.json`
- **Format**: JSON array of news articles
- **Structure**: One file per day
- **Advantages**:
  - Easy to manage and update
  - Resume-friendly (check file existence)
  - Can be filtered multiple times

### Filtered Stock News

- **Location**: `data/stocks/{category}/{stock_code}/YYYYMM.json`
- **Format**: JSON array of filtered news
- **Naming**: `{start_month}_{end_month}.json` or `{month}.json`
- **Filter Logic**: Uses stock code (e.g., "2330", "NVDA")

## API Information

### Available Categories

| Category | Description | Articles (2015-2025) |
|----------|-------------|---------------------|
| `tw_stock` | Taiwan stocks | ~22,848 |
| `us_stock` | US stocks | ~15,000+ |
| `hk_stock` | Hong Kong stocks | Available |
| `cn_stock` | China stocks | Available |
| `forex` | Foreign exchange | Available |
| `wd_stock` | World stocks | Available |



## Command Reference

### crawl_news.py

```bash
# Basic usage
python scripts/crawl_news.py --category CATEGORY --start YEAR --end YEAR

# Options
--category     News category (tw_stock, us_stock)
--start        Start year (default: 2015 for tw_stock, 2020 for us_stock)
--end          End year (default: current year)
--data-dir     Data directory (default: data)
--force        Force re-crawl existing data
```

### filter_stocks.py

```bash
# Basic usage
python scripts/filter_stocks.py --category CATEGORY --start DATE --end DATE

# Options
--category     News category (tw_stock, us_stock)
--start        Start date (YYYY-MM-DD, required)
--end          End date (YYYY-MM-DD, required)
--stock        Specific stock codes (optional)
--data-dir     Data directory (default: data)
```

### split_by_trading_day.py

```bash
# Basic usage
python scripts/split_by_trading_day.py --stock STOCK_CODE

# Options
--stock        Stock code (required, e.g., 2330)
--category     News category (default: tw_stock)
--start        Start date (YYYY-MM-DD, default: earliest news date)
--end          End date (YYYY-MM-DD, default: latest news date)
--data-dir     Data directory (default: data)
--finlab-key   Finlab API key (has default value)
```

**Output format** (`by_trading_day/YYYY-MM-DD.json`):
```json
{
  "trading_day": "2024-01-10",
  "news_window": {
    "start": "2024-01-09 13:30:00",
    "end": "2024-01-10 09:00:00"
  },
  "news_count": 4,
  "news": [...]
}
```

## Documentation

- [API Categories Guide](docs/API_CATEGORIES_GUIDE.md) - All available API categories
- [API Endpoints Comparison](docs/API_ENDPOINTS_COMPARISON.md) - Different API endpoints
- [Data Storage Guide](docs/DATA_STORAGE_GUIDE.md) - Storage strategies

## License

MIT License
