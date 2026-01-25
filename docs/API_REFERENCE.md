# Cnyes API Reference

## Available API Endpoints

### 1. Media API v1 (Free, No API Key Required)

**Base URL**: `https://api.cnyes.com/media/api/v1/newslist/category/{category}`

**Tested & Working Categories**:

| Category | Description | Articles (2015-2025) | Use Case |
|----------|-------------|---------------------|----------|
| `tw_stock` | Taiwan stocks | ~22,848 | Taiwan stock analysis |
| `us_stock` | US stocks | ~15,000+ | US stock analysis |
| `hk_stock` | Hong Kong stocks | Available | HK stock analysis |
| `cn_stock` | China stocks | Available | China stock analysis |
| `forex` | Foreign exchange | Available | Currency analysis |
| `fund` | Funds | Available | Fund analysis |
| `wd_stock` | World stocks | Available | International stocks |
| `headline` | All headlines | Available | General news |

**Parameters**:
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 30)
- `startAt`: Start timestamp (Unix timestamp)
- `endAt`: End timestamp (Unix timestamp)

**NOT Supported**:
- ❌ `keyword`: Keyword search (parameter is ignored by API)

**Example**:
```bash
# Get Taiwan stock news for 2024-12-31
curl "https://api.cnyes.com/media/api/v1/newslist/category/tw_stock?page=1&limit=30&startAt=1735574400&endAt=1735660799"
```

**Response Structure**:
```json
{
  "items": {
    "current_page": 1,
    "last_page": 192,
    "per_page": 30,
    "total": 5733,
    "data": [
      {
        "newsId": 5823323,
        "title": "News title",
        "content": "HTML content",
        "summary": "Summary text",
        "publishAt": 1735660799,
        "categoryName": "台股新聞",
        "keyword": ["台積電", "2330"]
      }
    ]
  }
}
```

---

### 2. ESS API (Free, Keyword Search)

**Base URL**: `https://ess.api.cnyes.com/ess/api/v1/news/keyword`

**Parameters**:
- `q`: Keyword (required)
- `page`: Page number
- `limit`: Items per page
- `startAt`: Start timestamp (Unix timestamp)
- `endAt`: End timestamp (Unix timestamp)

**Pros**:
- ✅ Server-side keyword filtering
- ✅ Full-text search (title + content + tags)
- ✅ Date range support

**Cons**:
- ⚠️ Full-text search = lower precision (36.7%)
- ⚠️ Returns news where keyword appears anywhere in content

**Example**:
```bash
curl "https://ess.api.cnyes.com/ess/api/v1/news/keyword?q=台積電&limit=30&page=1&startAt=1735574400&endAt=1735660799"
```

**When to Use**:
- Use if you need server-side filtering
- Use if you want news mentioning keyword anywhere in content
- **NOT recommended** for precise stock-specific news

---

### 3. OpenAPI (Requires API Key)

**Base URL**: `https://news.cnyes.com/openapi/api/v1/service/newslist`

**Documentation**: https://cnyes.com/api/frontend-api-doc/swagger

**Parameters**:
- `keyWord`: Keyword search (server-side)
- Other parameters similar to Media API

**Pros**:
- ✅ Official API
- ✅ Server-side keyword filtering
- ✅ More reliable

**Cons**:
- ❌ Requires API key application
- ❌ Contact: b2b-sales@anuegroup.com.tw

**When to Use**:
- If you need official support
- If server-side keyword filtering is critical
- If you can get API key

---

## Comparison

| Feature | Media API | ESS API | OpenAPI |
|---------|-----------|---------|---------|
| **API Key** | ❌ Not required | ❌ Not required | ✅ Required |
| **Keyword Search** | ❌ Not supported | ✅ Full-text search | ✅ Supported |
| **Date Range** | ✅ Supported | ✅ Supported | ✅ Supported |
| **Precision** | N/A | ⚠️ Low (36.7%) | ✅ High |
| **Speed** | ✅ Fast | ✅ Fast | ✅ Fast |
| **Historical Data** | ✅ 2009+ | ✅ 2009+ | ✅ 2009+ |

---

## Recommended Approach

**For this project, we use**: **Media API** + **Client-side filtering**

**Why**:
1. ✅ No API key required
2. ✅ Can filter by category (tw_stock, us_stock)
3. ✅ Client-side filtering is more precise
4. ✅ Save raw data once, filter multiple times

**Workflow**:
```
1. Download raw news using Media API
   → Saved to data/raw_tw_stock/YYYY/MM/YYYYMMDD.json

2. Filter by stock keywords (client-side)
   → Saved to data/stocks/tw_stock/{stock_code}_{stock_name}/

3. Use filtered data for analysis
```

---

## API Limitations

### Media API
- Max pages: No limit (but API returns `last_page`)
- Rate limit: Not officially documented (recommend 0.5s delay between requests)
- Timeout: 10 seconds recommended

### Best Practices
1. Always use delay between requests (`time.sleep(0.5)`)
2. Handle pagination properly (check `last_page`)
3. Cache/save raw data to avoid re-downloading
4. Use try-except for error handling

---

## Data Availability

### Taiwan Stocks (tw_stock)

| Year | Articles | Status |
|------|----------|--------|
| 2015 | 4,504 | ✅ Complete |
| 2016 | 1,744 | ✅ Complete |
| 2017 | 2,425 | ✅ Complete |
| 2018 | 2,146 | ✅ Complete |
| 2019 | 1,578 | ✅ Complete |
| 2020 | 1,867 | ✅ Complete |
| 2021 | 1,663 | ✅ Complete |
| 2022 | 1,644 | ✅ Complete |
| 2023 | 1,306 | ✅ Complete |
| 2024 | 1,845 | ✅ Complete |
| 2025 | 2,126 | ✅ Ongoing |

**Total**: 22,848 articles (2015-2025)

---

## Example Code

### Using Media API

```python
import requests
from datetime import datetime

def date_to_timestamp(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return int(dt.timestamp())

url = "https://api.cnyes.com/media/api/v1/newslist/category/tw_stock"
params = {
    'page': 1,
    'limit': 30,
    'startAt': date_to_timestamp("2024-12-01"),
    'endAt': date_to_timestamp("2024-12-31")
}

response = requests.get(url, params=params)
data = response.json()

# Get total pages
total_pages = data['items']['last_page']
total_articles = data['items']['total']

print(f"Total pages: {total_pages}")
print(f"Total articles: {total_articles}")
```

### Client-side Filtering

```python
# Filter by keyword
keyword = "台積電"
filtered = []

for item in data['items']['data']:
    title = item.get('title', '').lower()
    content = item.get('content', '').lower()
    summary = item.get('summary', '').lower()

    if keyword in title or keyword in content or keyword in summary:
        filtered.append(item)

print(f"Found {len(filtered)} articles about {keyword}")
```

---

## Notes

1. All APIs return news in reverse chronological order (newest first)
2. Timestamps are in Unix timestamp format (seconds since 1970-01-01)
3. Content may contain HTML tags, use BeautifulSoup to clean
4. Some news may appear in multiple categories
5. API response structure may change without notice
