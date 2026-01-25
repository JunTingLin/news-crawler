#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Split Stock News by Trading Day

Splits filtered stock news into individual JSON files per trading day.
Each trading day file contains news from previous day's close (13:30) to current day's open (09:00).

Uses finlab API to get actual Taiwan stock trading days.

Usage:
    python scripts/split_by_trading_day.py --stock 2330
    python scripts/split_by_trading_day.py --stock 2330 --start 2024-01-01 --end 2024-12-31
"""

import sys
import os
import argparse
import json
from datetime import datetime, time, timedelta
from pathlib import Path

from dotenv import load_dotenv
import finlab
from finlab import data

# Load .env file
load_dotenv()


# Trading hours
MARKET_CLOSE_TIME = time(13, 30)  # 13:30
MARKET_OPEN_TIME = time(9, 0)     # 09:00


def get_trading_days(start_date: str, end_date: str) -> list:
    """
    Get list of Taiwan stock trading days using finlab API

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        list: List of trading day dates (datetime.date objects)
    """
    # Get close price data to extract trading days
    close = data.get('price:收盤價')

    # Filter by date range
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    trading_days = []
    for ts in close.index:
        dt = ts.to_pydatetime()
        if start_dt <= dt <= end_dt:
            trading_days.append(dt.date())

    return sorted(trading_days)


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

    # Load all JSON files in the directory (except by_trading_day subdirectory)
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


def get_news_window(trading_day, prev_trading_day):
    """
    Calculate the news collection window for a trading day

    Args:
        trading_day: Current trading day (date object)
        prev_trading_day: Previous trading day (date object), None if first day

    Returns:
        tuple: (start_datetime, end_datetime) for news collection
    """
    # End time: trading_day 09:00 (before market open)
    end_dt = datetime.combine(trading_day, MARKET_OPEN_TIME)

    if prev_trading_day:
        # Start time: prev_trading_day 13:30 (after market close)
        start_dt = datetime.combine(prev_trading_day, MARKET_CLOSE_TIME)
    else:
        # First trading day: collect from beginning of that day
        start_dt = datetime.combine(trading_day, time(0, 0))

    return start_dt, end_dt


def filter_news_for_trading_day(all_news: list, start_dt: datetime, end_dt: datetime) -> list:
    """
    Filter news articles that fall within the time window

    Args:
        all_news: All news articles
        start_dt: Window start datetime
        end_dt: Window end datetime

    Returns:
        list: Filtered news articles sorted by publish_time
    """
    filtered = []

    for article in all_news:
        try:
            publish_time = parse_publish_time(article.get('publish_time', ''))
            if start_dt < publish_time <= end_dt:
                filtered.append(article)
        except (ValueError, TypeError):
            continue

    # Sort by publish_time
    filtered.sort(key=lambda x: x.get('publish_time', ''))

    return filtered


def save_trading_day_news(output_dir: Path, trading_day, news_list: list,
                          start_dt: datetime, end_dt: datetime) -> str:
    """
    Save news for a trading day

    Args:
        output_dir: Output directory
        trading_day: Trading day date
        news_list: List of news articles
        start_dt: Window start datetime
        end_dt: Window end datetime

    Returns:
        str: Saved file path or None if no news
    """
    # Create output with metadata
    output = {
        "trading_day": trading_day.strftime("%Y-%m-%d"),
        "news_window": {
            "start": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "end": end_dt.strftime("%Y-%m-%d %H:%M:%S")
        },
        "news_count": len(news_list),
        "news": news_list
    }

    # Save file
    filename = f"{trading_day.strftime('%Y-%m-%d')}.json"
    file_path = output_dir / filename

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return str(file_path)


def main():
    parser = argparse.ArgumentParser(description='Split stock news by trading day')
    parser.add_argument('--stock', type=str, required=True,
                        help='Stock code (e.g., 2330)')
    parser.add_argument('--category', type=str, default='tw_stock',
                        choices=['tw_stock'],
                        help='News category (default: tw_stock)')
    parser.add_argument('--start', type=str,
                        help='Start date (YYYY-MM-DD), default: earliest news date')
    parser.add_argument('--end', type=str,
                        help='End date (YYYY-MM-DD), default: latest news date')
    parser.add_argument('--data-dir', type=str, default='data',
                        help='Data directory (default: data)')
    parser.add_argument('--finlab-key', type=str,
                        default=os.getenv('FINLAB_API_KEY'),
                        help='Finlab API key (default: from FINLAB_API_KEY env var)')

    args = parser.parse_args()

    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "Split News by Trading Day" + " "*20 + "║")
    print("╚" + "="*78 + "╝")
    print()

    # Login to finlab
    print("Logging in to finlab...")
    finlab.login(args.finlab_key)
    print("✓ Logged in successfully")
    print()

    # Load stock news
    print(f"Loading news for stock {args.stock}...")
    all_news = load_stock_news(args.data_dir, args.category, args.stock)

    if not all_news:
        print("No news found. Please run filter_stocks.py first.")
        return

    print(f"✓ Loaded {len(all_news):,} articles total")
    print()

    # Determine date range from news if not specified
    news_dates = []
    for article in all_news:
        try:
            dt = parse_publish_time(article.get('publish_time', ''))
            news_dates.append(dt.date())
        except (ValueError, TypeError):
            continue

    if not news_dates:
        print("No valid news dates found")
        return

    min_date = min(news_dates)
    max_date = max(news_dates)

    start_date = args.start if args.start else min_date.strftime("%Y-%m-%d")
    end_date = args.end if args.end else max_date.strftime("%Y-%m-%d")

    print(f"News date range: {min_date} to {max_date}")
    print(f"Processing range: {start_date} to {end_date}")
    print()

    # Get trading days
    print("Fetching trading days from finlab...")
    # Extend start date to get previous trading day for first window
    extended_start = (datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=10)).strftime("%Y-%m-%d")
    trading_days = get_trading_days(extended_start, end_date)

    # Filter to requested range
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

    filtered_trading_days = [d for d in trading_days if start_dt <= d <= end_dt]

    print(f"✓ Found {len(filtered_trading_days)} trading days in range")
    print()

    # Create output directory
    output_dir = Path(args.data_dir) / "stocks" / args.category / args.stock / "by_trading_day"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")
    print()

    # Process each trading day
    print("="*80)
    print("Processing trading days...")
    print("="*80)

    stats = {
        "total_days": len(filtered_trading_days),
        "days_with_news": 0,
        "days_without_news": 0,
        "total_articles": 0
    }

    for i, trading_day in enumerate(filtered_trading_days):
        # Find previous trading day
        prev_trading_day = None
        for d in trading_days:
            if d < trading_day:
                prev_trading_day = d
            else:
                break

        # Get news window
        start_window, end_window = get_news_window(trading_day, prev_trading_day)

        # Filter news
        day_news = filter_news_for_trading_day(all_news, start_window, end_window)

        # Save
        file_path = save_trading_day_news(output_dir, trading_day, day_news, start_window, end_window)

        if day_news:
            stats["days_with_news"] += 1
            stats["total_articles"] += len(day_news)
            status = f"✓ {len(day_news):3d} articles"
        else:
            stats["days_without_news"] += 1
            status = "  (no news)"

        # Progress output (every 50 days or if has news)
        if (i + 1) % 50 == 0 or day_news:
            window_str = f"{start_window.strftime('%m/%d %H:%M')} ~ {end_window.strftime('%m/%d %H:%M')}"
            print(f"  {trading_day} [{window_str}]: {status}")

    # Summary
    print()
    print("="*80)
    print("Summary")
    print("="*80)
    print(f"Stock: {args.stock}")
    print(f"Date range: {start_date} to {end_date}")
    print(f"Trading days processed: {stats['total_days']}")
    print(f"Days with news: {stats['days_with_news']}")
    print(f"Days without news: {stats['days_without_news']}")
    print(f"Total articles saved: {stats['total_articles']}")
    print(f"Output directory: {output_dir}")
    print()
    print("✓ Done!")


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
