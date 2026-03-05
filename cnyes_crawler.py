"""
Cnyes News Crawler - Core Library

A crawler for cnyes.com news with the following features:
- Fetch news by category (tw_stock, us_stock, etc.)
- Filter news by keywords (client-side)
- Save news by date or keyword
- Support date range queries (2015+)
- No API key required
"""

import requests
import time
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Union
from pathlib import Path
from bs4 import BeautifulSoup
import html


class CnyesCrawler:
    """
    Cnyes News Crawler

    Main class for crawling news from cnyes.com using their free Media API.
    """

    def __init__(self, data_dir: str = "data"):
        """
        Initialize the crawler

        Args:
            data_dir: Base directory for saving data (default: "data")
        """
        self.base_url_v1 = "https://api.cnyes.com/media/api/v1"
        self.news_url = "https://news.cnyes.com/news/id"
        self.data_dir = Path(data_dir)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def _date_to_timestamp(self, date_str: str) -> int:
        """
        Convert date string to Unix timestamp

        Args:
            date_str: Date string in YYYY-MM-DD format

        Returns:
            Unix timestamp (int)
        """
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return int(dt.timestamp())

    def _match_keyword(self, item: Dict, keyword) -> bool:
        """
        Check if news item matches keyword(s)

        Search scope: title, content, summary

        Args:
            item: News item dict with 'title', 'content', 'summary' fields
            keyword: Can be:
                - None: Match all news
                - str: Single keyword (e.g., "台積電")
                - list: Multiple keywords with OR logic (e.g., ["台新金", "新光金"])
                       ANY keyword appearing in the news will match
                - tuple: (include_list, exclude_list) for include/exclude logic
                       e.g., (["南亞"], ["南亞科"]) matches "南亞" but excludes "南亞科"

        Returns:
            bool: True if keyword matches
        """
        # Match all if no keyword specified
        if keyword is None:
            return True

        # Get text fields from news item
        title = (item.get('title', '') or '').lower()
        content = (item.get('content', '') or '').lower()
        summary = (item.get('summary', '') or '').lower()

        # Combine all text fields for searching
        combined_text = f"{title} {content} {summary}"

        # Single keyword matching
        if isinstance(keyword, str):
            kw = keyword.lower()
            return kw in combined_text

        # Tuple format: (include_list, exclude_list)
        elif isinstance(keyword, tuple) and len(keyword) == 2:
            include_list, exclude_list = keyword

            # Check exclude first - if any exclude keyword is found, return False
            for ex_kw in exclude_list:
                if ex_kw and ex_kw.lower() in combined_text:
                    return False

            # Check include - if any include keyword is found, return True
            for in_kw in include_list:
                if in_kw and in_kw.lower() in combined_text:
                    return True

            return False  # No include keywords found

        # List format: Multiple keywords with OR logic
        elif isinstance(keyword, list):
            for kw in keyword:
                kw_lower = kw.lower()
                if kw_lower in combined_text:
                    return True  # If any keyword is found, return True
            return False  # No keywords found

        return False

    def get_all_news(
        self,
        start_date: str,
        end_date: str,
        limit: int = 30,
        max_pages: int = None,
        delay: float = 0.5,
        category: str = "headline"
    ) -> List[Dict]:
        """
        Fetch all news in date range (without keyword filtering)

        Recommended workflow:
        1. Use this method to fetch all news once
        2. Use filter_news() to filter by different keywords

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            limit: Items per page (default: 30)
            max_pages: Maximum pages to fetch (default: None = fetch all)
            delay: Delay between requests in seconds (default: 0.5)
            category: News category (default: "headline")
                Options: "headline", "tw_stock", "us_stock", "hk_stock",
                        "cn_stock", "forex", "fund", "wd_stock"

        Returns:
            List of news items (list of dicts)
        """
        all_news = []
        page = 1
        start_ts = self._date_to_timestamp(start_date)
        end_ts = self._date_to_timestamp(end_date)

        print(f"Fetching all news")
        print(f"Date range: {start_date} to {end_date}")
        print(f"Category: {category}")
        print("-" * 60)

        while True:
            url = f"{self.base_url_v1}/newslist/category/{category}"
            params = {
                'page': page,
                'limit': limit,
                'startAt': start_ts,
                'endAt': end_ts
            }

            try:
                print(f"Fetching page {page}...", end=' ')
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                # Check if data exists
                if 'items' not in data or 'data' not in data['items']:
                    print("No data received")
                    break

                items = data['items']['data']
                if not items:
                    print("No more data")
                    break

                print(f"Got {len(items)} articles")

                # Parse all news items
                for item in items:
                    news_data = self._parse_news_item(item)
                    all_news.append(news_data)

                # Check if there are more pages
                total_pages = data['items'].get('last_page', page)
                if page >= total_pages:
                    print("Reached last page")
                    break

                # Check if reached max_pages limit
                if max_pages and page >= max_pages:
                    print(f"Reached max pages limit: {max_pages}")
                    break

                page += 1
                time.sleep(delay)

            except requests.exceptions.RequestException as e:
                print(f"\nRequest error: {e}")
                break
            except Exception as e:
                print(f"\nData processing error: {e}")
                break

        print("-" * 60)
        print(f"Total fetched: {len(all_news)} articles")
        return all_news

    def filter_news(
        self,
        news_list: List[Dict],
        keyword,
        fetch_content: bool = False,
        delay: float = 0.5
    ) -> List[Dict]:
        """
        Filter news by keyword(s) from pre-fetched news list

        This method avoids duplicate API calls, suitable for multi-keyword search.

        Args:
            news_list: List of news items (from get_all_news())
            keyword: Keyword(s) to filter:
                - str: Single keyword (e.g., "台積電")
                - list: Multiple keywords with OR logic (e.g., ["台新金", "新光金"])
                       ANY keyword appearing in the news will match
                - tuple: (include_list, exclude_list) for include/exclude logic
                       e.g., (["南亞"], ["南亞科"]) matches "南亞" but excludes "南亞科"
            fetch_content: Whether to fetch full content from web page (default: False)
            delay: Delay between requests when fetching content (default: 0.5)

        Returns:
            Filtered news list
        """
        filtered = []

        # Display filter info
        if isinstance(keyword, tuple) and len(keyword) == 2:
            include_list, exclude_list = keyword
            include_str = ' OR '.join(include_list) if include_list else 'None'
            exclude_str = ' OR '.join(exclude_list) if exclude_list else 'None'
            print(f"Filtering: INCLUDE({include_str}) EXCLUDE({exclude_str})")
        elif isinstance(keyword, list):
            print(f"Filtering keywords (OR): {' OR '.join(keyword)}")
        else:
            print(f"Filtering keyword: {keyword}")

        for news in news_list:
            # Convert news to item format for matching
            item = {
                'title': news.get('title', ''),
                'content': news.get('content', ''),
                'summary': news.get('summary', '')
            }

            if self._match_keyword(item, keyword):
                # Fetch full content if requested
                if fetch_content and news.get('news_id') and 'full_content' not in news:
                    time.sleep(delay)
                    full_content = self._fetch_news_content(news['news_id'])
                    if full_content:
                        news['full_content'] = full_content

                filtered.append(news)

        print(f"Found {len(filtered)} matching articles")
        return filtered

    def _parse_news_item(self, item: Dict) -> Dict:
        """
        Parse news item from API response

        Args:
            item: Raw news item from API

        Returns:
            Parsed news item dict
        """
        news_id = item.get('newsId')
        title = item.get('title', '')
        content_html = item.get('content', '')
        summary = item.get('summary', '')
        publish_at = item.get('publishAt', 0)
        category_name = item.get('categoryName', '')
        keywords = item.get('keyword', [])

        # Convert HTML content to plain text
        content_text = self._html_to_text(content_html)

        # Format publish time
        publish_time = datetime.fromtimestamp(publish_at).strftime('%Y-%m-%d %H:%M:%S') if publish_at else ''

        return {
            'news_id': news_id,
            'title': title,
            'summary': summary,
            'content': content_text,
            'publish_time': publish_time,
            'category': category_name,
            'keywords': keywords,
            'url': f"{self.news_url}/{news_id}" if news_id else ''
        }

    def _html_to_text(self, html_content: str) -> str:
        """
        Convert HTML content to plain text

        Args:
            html_content: HTML string

        Returns:
            Plain text string
        """
        if not html_content:
            return ""

        text = html.unescape(html_content)
        soup = BeautifulSoup(text, 'html.parser')

        # Remove script and style tags
        for script in soup(['script', 'style']):
            script.decompose()

        # Get text and clean up whitespace
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        return text

    def _fetch_news_content(self, news_id: int) -> Optional[str]:
        """
        Fetch full news content from web page

        Args:
            news_id: News ID

        Returns:
            Full content text, or None if failed
        """
        url = f"{self.news_url}/{news_id}"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Try multiple content selectors
            content_selectors = [
                'div._1YbA',
                'div.news-content',
                'div.article-body',
                'div[itemprop="articleBody"]',
                'article'
            ]

            content = None
            for selector in content_selectors:
                content_div = soup.select_one(selector)
                if content_div:
                    content = content_div.get_text(strip=True)
                    break

            # Fallback: find any div with substantial text
            if not content:
                for div in soup.find_all('div'):
                    text = div.get_text(strip=True)
                    if len(text) > 200:
                        content = text
                        break

            return content

        except Exception as e:
            print(f"Failed to fetch content (ID: {news_id}): {e}")
            return None

    def save_news_by_date(
        self,
        news_list: List[Dict],
        storage_type: str = "json",
        data_type: str = "raw"
    ) -> Dict[str, int]:
        """
        Save news by date (one file per day)

        File structure: data/{data_type}/YYYY/MM/YYYYMMDD.json

        Args:
            news_list: List of news items
            storage_type: Storage format ("json" or "parquet")
            data_type: Data type folder name (e.g., "raw", "raw_tw_stock")

        Returns:
            Statistics dict {date: count}
        """
        if storage_type not in ["json", "parquet"]:
            raise ValueError("storage_type must be 'json' or 'parquet'")

        # Group news by date
        news_by_date = {}
        for news in news_list:
            publish_time = news.get('publish_time', '')
            if not publish_time:
                continue

            # Extract date part (YYYY-MM-DD)
            date_str = publish_time.split()[0]
            if date_str not in news_by_date:
                news_by_date[date_str] = []
            news_by_date[date_str].append(news)

        # Save statistics
        stats = {}

        # Save each date
        for date_str, daily_news in news_by_date.items():
            try:
                # Parse date
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                year = date_obj.strftime("%Y")
                month = date_obj.strftime("%m")
                date_file = date_obj.strftime("%Y%m%d")

                # Create directory: data/{data_type}/YYYY/MM/
                dir_path = self.data_dir / data_type / year / month
                dir_path.mkdir(parents=True, exist_ok=True)

                # Save file
                if storage_type == "json":
                    file_path = dir_path / f"{date_file}.json"
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(daily_news, f, ensure_ascii=False, indent=2)
                    stats[date_str] = len(daily_news)
                    print(f"✓ {date_str}: Saved {len(daily_news)} articles -> {file_path}")

                elif storage_type == "parquet":
                    try:
                        import pandas as pd
                        file_path = dir_path / f"{date_file}.parquet"
                        df = pd.DataFrame(daily_news)
                        df.to_parquet(file_path, index=False, engine='pyarrow')
                        stats[date_str] = len(daily_news)
                        print(f"✓ {date_str}: Saved {len(daily_news)} articles -> {file_path}")
                    except ImportError:
                        print("⚠ Parquet format requires pandas and pyarrow")
                        print("  Run: pip install pandas pyarrow")
                        return {}

            except Exception as e:
                print(f"✗ {date_str}: Save failed - {e}")

        return stats

    def save_news_by_keyword(
        self,
        news_list: List[Dict],
        keyword_name: str,
        start_date: str = None,
        end_date: str = None,
        storage_type: str = "json"
    ) -> str:
        """
        Save news by keyword (for filtered news)

        File structure: data/processed/{keyword_name}_YYYYMM.json

        Args:
            news_list: List of news items
            keyword_name: Keyword name (e.g., "台積電")
            start_date: Start date (for filename)
            end_date: End date (for filename)
            storage_type: Storage format ("json" or "parquet")

        Returns:
            Saved file path
        """
        if not news_list:
            print(f"⚠ {keyword_name}: No news to save")
            return ""

        # Create directory
        dir_path = self.data_dir / "processed"
        dir_path.mkdir(parents=True, exist_ok=True)

        # Generate filename
        if start_date and end_date:
            # Extract YYYYMM
            start_ym = start_date.replace("-", "")[:6]  # YYYYMM
            end_ym = end_date.replace("-", "")[:6]
            if start_ym == end_ym:
                filename = f"{keyword_name}_{start_ym}"
            else:
                filename = f"{keyword_name}_{start_ym}_{end_ym}"
        else:
            # Use current timestamp
            filename = f"{keyword_name}_{datetime.now().strftime('%Y%m%d')}"

        # Save file
        try:
            if storage_type == "json":
                file_path = dir_path / f"{filename}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(news_list, f, ensure_ascii=False, indent=2)
                print(f"✓ {keyword_name}: Saved {len(news_list)} articles -> {file_path}")
                return str(file_path)

            elif storage_type == "parquet":
                try:
                    import pandas as pd
                    file_path = dir_path / f"{filename}.parquet"
                    df = pd.DataFrame(news_list)
                    df.to_parquet(file_path, index=False, engine='pyarrow')
                    print(f"✓ {keyword_name}: Saved {len(news_list)} articles -> {file_path}")
                    return str(file_path)
                except ImportError:
                    print("⚠ Parquet format requires pandas and pyarrow")
                    print("  Run: pip install pandas pyarrow")
                    return ""
        except Exception as e:
            print(f"✗ {keyword_name}: Save failed - {e}")
            return ""

    def load_news_by_date(
        self,
        date_str: str,
        storage_type: str = "json",
        data_type: str = "raw"
    ) -> List[Dict]:
        """
        Load news for specific date

        Args:
            date_str: Date string in YYYY-MM-DD format
            storage_type: Storage format ("json" or "parquet")
            data_type: Data type folder name

        Returns:
            List of news items
        """
        try:
            # Parse date
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            year = date_obj.strftime("%Y")
            month = date_obj.strftime("%m")
            date_file = date_obj.strftime("%Y%m%d")

            # File path
            if storage_type == "json":
                file_path = self.data_dir / data_type / year / month / f"{date_file}.json"
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                else:
                    print(f"⚠ File not found: {file_path}")
                    return []

            elif storage_type == "parquet":
                try:
                    import pandas as pd
                    file_path = self.data_dir / data_type / year / month / f"{date_file}.parquet"
                    if file_path.exists():
                        df = pd.read_parquet(file_path)
                        return df.to_dict('records')
                    else:
                        print(f"⚠ File not found: {file_path}")
                        return []
                except ImportError:
                    print("⚠ Parquet format requires pandas and pyarrow")
                    return []

        except Exception as e:
            print(f"✗ Load failed: {e}")
            return []
