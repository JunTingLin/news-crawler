#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Split Stock News by Trading Day (V2)

Splits filtered stock news into individual JSON files per trading day.
Each file contains all news from that calendar day (00:00 ~ 23:59:59).

Uses finlab 0050 for Taiwan trading days, Yahoo Finance for US stocks.

Usage:
    python scripts/split_by_trading_day_v2.py --stock 2330
    python scripts/split_by_trading_day_v2.py --stock 2330 --start 2024-01-01 --end 2024-12-31
    python scripts/split_by_trading_day_v2.py --stock AAPL --category us_stock
"""

import sys
import os
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

import yfinance as yf
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.filter_stocks import TWII_STOCKS

# Load environment variables
load_dotenv()


def get_stock_name(stock_code: str) -> str:
    """Get stock name from TWII_STOCKS, fallback to stock_code"""
    if stock_code in TWII_STOCKS:
        include_list, _ = TWII_STOCKS[stock_code]
        return include_list[0] if include_list else stock_code
    return stock_code


def extract_context_around_keyword(content: str, keywords: list, context_chars: int = 150) -> str:
    """
    Extract text around keyword occurrences in content.

    Args:
        content: Full article content
        keywords: List of keywords to search for (e.g., ['台積電', '2330'])
        context_chars: Number of characters before and after keyword

    Returns:
        Extracted context string, or empty string if no keyword found
    """
    content_lower = content.lower()
    found_positions = []

    for keyword in keywords:
        keyword_lower = keyword.lower()
        pos = 0
        while True:
            pos = content_lower.find(keyword_lower, pos)
            if pos == -1:
                break
            found_positions.append((pos, len(keyword)))
            pos += 1

    if not found_positions:
        return ""

    # Sort by position
    found_positions.sort()

    # Extract context for first occurrence (most relevant)
    pos, keyword_len = found_positions[0]
    start = max(0, pos - context_chars)
    end = min(len(content), pos + keyword_len + context_chars)

    snippet = content[start:end]

    # Add ellipsis if truncated
    if start > 0:
        snippet = "..." + snippet
    if end < len(content):
        snippet = snippet + "..."

    return snippet


def add_extracted_content(news_list: list, stock_code: str, context_chars: int = 150) -> list:
    """
    Add extracted_content field to each news article.

    Args:
        news_list: List of news articles
        stock_code: Stock code (e.g., '2330')
        context_chars: Characters before/after keyword

    Returns:
        List with extracted_content added to each article
    """
    # Use all keywords from TWII_STOCKS include_list + stock_code
    if stock_code in TWII_STOCKS:
        include_list, _ = TWII_STOCKS[stock_code]
        keywords = list(include_list) + [stock_code]
    else:
        keywords = [stock_code]

    for article in news_list:
        content = article.get('content', '').strip()
        if not content:
            content = article.get('summary', '').strip()

        if not content:
            article['extracted_content'] = ''
            continue

        # Try to extract context around keyword
        snippet = extract_context_around_keyword(content, keywords, context_chars)

        # Fallback: if keyword not found, use first N chars
        if not snippet:
            max_fallback = context_chars * 2
            if len(content) > max_fallback:
                snippet = content[:max_fallback] + "..."
            else:
                snippet = content

        article['extracted_content'] = snippet

    return news_list


def get_trading_days_finlab(start_date: str, end_date: str) -> list:
    """
    Get list of trading days using finlab 0050 data

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        list: List of trading day date strings (YYYY-MM-DD)
    """
    import finlab
    from finlab import data

    # Login to finlab
    api_key = os.getenv('FINLAB_API_KEY')
    if not api_key:
        raise Exception("FINLAB_API_KEY not found in environment variables")
    finlab.login(api_key)

    # Get 0050 close price as trading day reference
    close = data.get('price:收盤價')['0050']

    # Filter by date range (don't use dropna to avoid excluding days during stock splits)
    mask = (close.index >= start_date) & (close.index <= end_date)
    trading_days = close[mask].index

    return sorted([d.strftime("%Y-%m-%d") for d in trading_days])


def get_trading_days_yfinance(index_symbol: str, start_date: str, end_date: str) -> list:
    """
    Get list of trading days using Yahoo Finance

    Args:
        index_symbol: Index symbol (e.g., ^DJIA)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        list: List of trading day date strings (YYYY-MM-DD)
    """
    ticker = yf.Ticker(index_symbol)
    # Add one day to end_date since yfinance end is exclusive
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    end_date_plus1 = end_dt.strftime("%Y-%m-%d")
    hist = ticker.history(start=start_date, end=end_date_plus1)

    trading_days = []
    for ts in hist.index:
        trading_days.append(ts.strftime("%Y-%m-%d"))

    return sorted(set(trading_days))


def get_trading_days(category: str, start_date: str, end_date: str, index_symbol: str = None) -> list:
    """
    Get list of trading days based on category

    Args:
        category: Stock category (tw_stock, us_stock)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        index_symbol: Optional custom index symbol for yfinance

    Returns:
        list: List of trading day date strings (YYYY-MM-DD)
    """
    if category == 'tw_stock' and index_symbol is None:
        # Use finlab 0050 for Taiwan stocks
        return get_trading_days_finlab(start_date, end_date)
    else:
        # Use Yahoo Finance for US stocks or custom index
        symbol = index_symbol if index_symbol else '^DJIA'
        return get_trading_days_yfinance(symbol, start_date, end_date)


def load_stock_news(data_dir: str, category: str, stock_code: str) -> list:
    """
    Load all news for a stock from existing filtered files

    Args:
        data_dir: Base data directory
        category: News category (tw_stock, us_stock)
        stock_code: Stock code

    Returns:
        list: All news articles for this stock
    """
    stock_dir = Path(data_dir) / "stocks" / category / stock_code

    if not stock_dir.exists():
        print(f"Stock directory not found: {stock_dir}")
        return []

    all_news = []

    # Load all JSON files in the directory
    for json_file in stock_dir.glob("*.json"):
        if json_file.is_file():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    news = json.load(f)
                    all_news.extend(news)
                    print(f"  Loaded {len(news):,} articles from {json_file.name}")
            except Exception as e:
                print(f"  Error loading {json_file}: {e}")

    # Remove duplicates by news_id
    seen_ids = set()
    unique_news = []
    for article in all_news:
        news_id = article.get('news_id')
        if news_id and news_id not in seen_ids:
            seen_ids.add(news_id)
            unique_news.append(article)

    if len(all_news) != len(unique_news):
        print(f"  Removed {len(all_news) - len(unique_news)} duplicates")

    return unique_news


def parse_publish_time(publish_time: str) -> datetime:
    """Parse publish_time string to datetime object"""
    return datetime.strptime(publish_time, "%Y-%m-%d %H:%M:%S")


def group_news_by_date(all_news: list) -> dict:
    """
    Group news articles by publish date

    Args:
        all_news: All news articles

    Returns:
        dict: {date_str: [articles]}
    """
    grouped = defaultdict(list)

    for article in all_news:
        try:
            publish_time = article.get('publish_time', '')
            dt = parse_publish_time(publish_time)
            date_str = dt.strftime("%Y-%m-%d")
            grouped[date_str].append(article)
        except (ValueError, TypeError):
            continue

    # Sort articles within each date
    for date_str in grouped:
        grouped[date_str].sort(key=lambda x: x.get('publish_time', ''))

    return grouped


def save_day_news(output_dir: Path, date_str: str, news_list: list,
                  stock_code: str, context_chars: int) -> str:
    """
    Save news for a trading day

    Args:
        output_dir: Output directory
        date_str: Date string (YYYY-MM-DD)
        news_list: List of news articles
        stock_code: Stock code for extracting relevant content
        context_chars: Characters before/after keyword for extraction

    Returns:
        str: Saved file path
    """
    # Add extracted_content to each article
    news_with_extract = add_extracted_content(news_list, stock_code, context_chars)

    # Create output with metadata
    output = {
        "trading_day": date_str,
        "news_window": {
            "start": f"{date_str} 00:00:00",
            "end": f"{date_str} 23:59:59"
        },
        "news_count": len(news_with_extract),
        "news": news_with_extract
    }

    # Save file
    filename = f"{date_str}.json"
    file_path = output_dir / filename

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return str(file_path)


def main():
    parser = argparse.ArgumentParser(description='Split stock news by trading day (V2)')
    parser.add_argument('--stock', type=str, required=True,
                        help='Stock code (e.g., 2330, AAPL)')
    parser.add_argument('--category', type=str, default='tw_stock',
                        help='News category (default: tw_stock)')
    parser.add_argument('--start', type=str,
                        help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str,
                        help='End date (YYYY-MM-DD)')
    parser.add_argument('--data-dir', type=str, default='data',
                        help='Data directory (default: data)')
    parser.add_argument('--context-chars', type=int, default=150,
                        help='Chars before/after stock mention for extracted_content (default: 150)')
    parser.add_argument('--index', type=str,
                        help='Custom index symbol for trading days (uses finlab 0050 for tw_stock by default)')

    args = parser.parse_args()

    # Determine trading day source
    if args.category == 'tw_stock' and args.index is None:
        trading_day_source = "finlab 0050"
    else:
        trading_day_source = args.index if args.index else "^DJIA"

    print("=" * 60)
    print(f"Split News by Trading Day (V2) - {args.stock}")
    print("=" * 60)
    print(f"Trading day source: {trading_day_source}")
    print()

    # Load stock news
    print(f"Loading news for stock {args.stock}...")
    all_news = load_stock_news(args.data_dir, args.category, args.stock)

    if not all_news:
        print("No news found. Please run filter_stocks.py first.")
        return

    print(f"Loaded {len(all_news):,} articles total")
    print()

    # Group by date
    print("Grouping news by date...")
    grouped = group_news_by_date(all_news)
    print(f"Found {len(grouped)} unique dates with news")
    print()

    # Determine date range
    all_dates = sorted(grouped.keys())
    start_date = args.start if args.start else all_dates[0]
    end_date = args.end if args.end else all_dates[-1]

    print(f"Date range: {start_date} ~ {end_date}")
    print()

    # Get trading days
    print(f"Fetching trading days ({trading_day_source})...")
    trading_days = get_trading_days(args.category, start_date, end_date, args.index)
    print(f"Found {len(trading_days)} trading days")
    print()

    # Create output directory
    output_dir = Path(args.data_dir) / "stocks" / args.category / "by_trading_day" / args.stock
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")
    print(f"Context chars: {args.context_chars}")
    print()

    # Save each trading day
    print("Saving trading day files...")
    total_articles = 0
    days_with_news = 0
    days_without_news = 0

    for i, date_str in enumerate(trading_days):
        news_list = grouped.get(date_str, [])
        save_day_news(output_dir, date_str, news_list, args.stock, args.context_chars)

        if news_list:
            days_with_news += 1
            total_articles += len(news_list)
        else:
            days_without_news += 1

        # Progress every 100 days
        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}/{len(trading_days)} trading days...")

    # Summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Stock: {args.stock}")
    print(f"Trading day source: {trading_day_source}")
    print(f"Trading days: {len(trading_days)}")
    print(f"Days with news: {days_with_news}")
    print(f"Days without news: {days_without_news}")
    print(f"Total articles: {total_articles:,}")
    print(f"Output: {output_dir}")
    print()
    print("Done!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
