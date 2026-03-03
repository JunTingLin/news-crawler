#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock News Filter

Filters raw news data by stock keywords and saves to data/stocks/{stock_name}/
Supports Taiwan stocks and US stocks.

Usage:
    python scripts/filter_stocks.py --category tw_stock --start 2024-01-01 --end 2024-12-31
    python scripts/filter_stocks.py --category us_stock --stock NVDA TSLA
"""

import sys
import os
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cnyes_crawler import CnyesCrawler


# 2016-01-01~2025-12-31 intersect TWII stocks list
# Format: "stock_code": ["code", "chinese_name"]
# Using AND logic: both code and name must appear in the news
TWII_STOCKS = {
    "1216": ["1216", "統一"],
    "1301": ["1301", "台塑"],
    "1303": ["1303", "南亞"],
    "2002": ["2002", "中鋼"],
    "2303": ["2303", "聯電"],
    "2308": ["2308", "台達電"],
    "2317": ["2317", "鴻海"],
    "2330": ["2330", "台積電"],
    "2357": ["2357", "華碩"],
    "2382": ["2382", "廣達"],
    "2395": ["2395", "研華"],
    "2412": ["2412", "中華電"],
    "2454": ["2454", "聯發科"],
    "2880": ["2880", "華南金"],
    "2881": ["2881", "富邦金"],
    "2882": ["2882", "國泰金"],
    "2884": ["2884", "玉山金"],
    "2885": ["2885", "元大金"],
    "2886": ["2886", "兆豐金"],
    "2887": ["2887", "台新新光金"],
    "2891": ["2891", "中信金"],
    "2892": ["2892", "第一金"],
    "2912": ["2912", "統一超"],
    "3008": ["3008", "大立光"],
    "3045": ["3045", "台灣大"],
    "3711": ["3711", "日月光投控"],
    "4904": ["4904", "遠傳"],
    "5880": ["5880", "合庫金"],
    "6505": ["6505", "台塑化"],
}

# US stock configurations
US_STOCKS = {
    "NVDA": ["NVDA"],
    "TSLA": ["TSLA"],
    "AAPL": ["AAPL"],
    "MSFT": ["MSFT"],
    "GOOGL": ["GOOGL"],
    "META": ["META"],
    "AMZN": ["AMZN"],
}

# Title keywords to exclude (table-type articles with massive content)
EXCLUDE_TITLE_KEYWORDS = [
    "一覽表",
    "淨值表",
    "[表一",
    "[表二",
    "[表三",
    "基金淨值",
]


def load_news_from_date(data_dir, category, date_str):
    """
    Load news from raw data file for a specific date

    Args:
        data_dir: Base data directory
        category: News category (tw_stock, us_stock)
        date_str: Date string in YYYY-MM-DD format

    Returns:
        list: List of news articles, empty if file not found
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        year = date_obj.strftime("%Y")
        month = date_obj.strftime("%m")
        date_file = date_obj.strftime("%Y%m%d")

        file_path = Path(data_dir) / f"raw_{category}" / year / month / f"{date_file}.json"

        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return []
    except Exception as e:
        print(f"Error loading {date_str}: {e}")
        return []


def load_news_range(data_dir, category, start_date, end_date):
    """
    Load all news in date range

    Args:
        data_dir: Base data directory
        category: News category
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)

    Returns:
        list: Combined list of all news articles
    """
    all_news = []

    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    print(f"Loading raw news from {start_date} to {end_date}...")

    days_loaded = 0
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        news = load_news_from_date(data_dir, category, date_str)

        if news:
            all_news.extend(news)
            days_loaded += 1

        current += timedelta(days=1)

    print(f"✓ Loaded {len(all_news):,} articles from {days_loaded} days")
    return all_news


def should_exclude_article(article):
    """
    Check if article should be excluded based on title keywords

    Args:
        article: News article dict

    Returns:
        bool: True if should be excluded
    """
    title = article.get('title', '')
    for keyword in EXCLUDE_TITLE_KEYWORDS:
        if keyword in title:
            return True
    return False


def filter_by_stock(crawler, all_news, keywords_list):
    """
    Filter news by stock keywords

    Args:
        crawler: CnyesCrawler instance
        all_news: List of all news articles
        keywords_list: List of keywords to search (e.g., ["2330"], ["2330", "台積電"])

    Returns:
        list: Filtered news articles
    """
    # Filter news using the provided keywords list
    filtered = crawler.filter_news(all_news, keywords_list)

    # Exclude table-type articles
    original_count = len(filtered)
    filtered = [article for article in filtered if not should_exclude_article(article)]
    excluded_count = original_count - len(filtered)

    if excluded_count > 0:
        print(f"  (excluded {excluded_count} table-type articles)")

    return filtered


def save_stock_news(data_dir, category, stock_code, news_list, start_date, end_date):
    """
    Save filtered stock news to file

    Args:
        data_dir: Base data directory
        category: News category
        stock_code: Stock code (folder name will be just the code)
        news_list: List of news articles
        start_date: Start date
        end_date: End date

    Returns:
        str: Saved file path
    """
    if not news_list:
        return None

    # Create directory: data/stocks/{category}/{stock_code}/
    stock_dir = Path(data_dir) / "stocks" / category / stock_code
    stock_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    start_ym = start_date.replace("-", "")[:6]  # YYYYMM
    end_ym = end_date.replace("-", "")[:6]

    if start_ym == end_ym:
        filename = f"{start_ym}.json"
    else:
        filename = f"{start_ym}_{end_ym}.json"

    file_path = stock_dir / filename

    # Save to JSON
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)

    return str(file_path)


def main():
    parser = argparse.ArgumentParser(description='Filter stock news from raw data')
    parser.add_argument('--category', type=str, default='tw_stock',
                        choices=['tw_stock', 'us_stock'],
                        help='News category (default: tw_stock)')
    parser.add_argument('--start', type=str, required=True,
                        help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, required=True,
                        help='End date (YYYY-MM-DD)')
    parser.add_argument('--stock', nargs='+',
                        help='Specific stock codes to filter (e.g., 2330 2454)')
    parser.add_argument('--data-dir', type=str, default='data',
                        help='Data directory (default: data)')

    args = parser.parse_args()

    print("╔" + "="*78 + "╗")
    print("║" + " "*25 + "Stock Filter" + " "*25 + "║")
    print("╚" + "="*78 + "╝")
    print()
    print(f"Category: {args.category}")
    print(f"Date range: {args.start} to {args.end}")
    print(f"Data directory: {args.data_dir}")
    print()

    # Select stock list
    if args.category == 'tw_stock':
        stock_list = TWII_STOCKS
    elif args.category == 'us_stock':
        stock_list = US_STOCKS
    else:
        print(f"Unknown category: {args.category}")
        return

    # Filter specific stocks if provided
    if args.stock:
        stock_list = {code: keywords for code, keywords in stock_list.items()
                     if code in args.stock}

        if not stock_list:
            print(f"No matching stocks found for: {args.stock}")
            return

    print(f"Stocks to filter: {len(stock_list)}")
    for code, keywords in stock_list.items():
        print(f"  - {code}: {keywords}")
    print()

    # Load all news in date range
    all_news = load_news_range(args.data_dir, args.category, args.start, args.end)

    if not all_news:
        print("No news found in date range. Please crawl raw data first.")
        print(f"Run: python scripts/crawl_news.py --category {args.category}")
        return

    # Initialize crawler
    crawler = CnyesCrawler(data_dir=args.data_dir)

    # Filter and save for each stock
    print("\n" + "="*80)
    print("Filtering stocks...")
    print("="*80)

    results = {}

    for stock_code, keywords_list in stock_list.items():
        print(f"\n{stock_code} (keywords: {keywords_list}):")
        print("-" * 60)

        # Filter news
        filtered_news = filter_by_stock(crawler, all_news, keywords_list)

        print(f"Found {len(filtered_news)} articles")

        if filtered_news:
            # Save to file
            file_path = save_stock_news(
                args.data_dir,
                args.category,
                stock_code,
                filtered_news,
                args.start,
                args.end
            )

            print(f"✓ Saved to: {file_path}")
            results[stock_code] = len(filtered_news)
        else:
            print("⚠ No news found")
            results[stock_code] = 0

    # Summary
    print("\n" + "="*80)
    print("Summary")
    print("="*80)
    print(f"\nTotal articles processed: {len(all_news):,}")
    print(f"Stocks filtered: {len(stock_list)}")
    print()

    # Sort by news count
    sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)

    print("Articles by stock:")
    for stock_code, count in sorted_results:
        keywords_list = stock_list[stock_code]
        keywords_str = ', '.join(keywords_list)
        print(f"  {stock_code:6s} ({keywords_str:20s}): {count:5,} articles")

    total_filtered = sum(results.values())
    print(f"\nTotal filtered: {total_filtered:,} articles")

    # Note about duplicates
    if total_filtered > len(all_news):
        duplicates = total_filtered - len(all_news)
        print(f"Note: {duplicates:,} articles mentioned multiple stocks")


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
