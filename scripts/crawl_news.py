#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
News Crawler with Resume Capability

Crawls news from cnyes.com and saves to data/raw/{category}/YYYY/MM/YYYYMMDD.json
Supports resuming from interruption by checking existing files.

Usage:
    python scripts/crawl_news.py --category tw_stock --start 2015 --end 2025
    python scripts/crawl_news.py --category us_stock --start 2024 --end 2025
"""

import sys
import os
import argparse
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path to import cnyes_crawler_final
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cnyes_crawler import CnyesCrawler


# Stock category configurations
CATEGORY_CONFIG = {
    'tw_stock': {
        'name': 'Taiwan Stock News',
        'default_start': 2015,
        'default_end': datetime.now().year
    },
    'us_stock': {
        'name': 'US Stock News',
        'default_start': 2020,
        'default_end': datetime.now().year
    },
}


def check_file_exists(data_dir, category, date_str):
    """
    Check if news file already exists for given date

    Args:
        data_dir: Base data directory
        category: News category (tw_stock, us_stock)
        date_str: Date string in YYYY-MM-DD format

    Returns:
        bool: True if file exists
    """
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    year = date_obj.strftime("%Y")
    month = date_obj.strftime("%m")
    date_file = date_obj.strftime("%Y%m%d")

    file_path = Path(data_dir) / f"raw_{category}" / year / month / f"{date_file}.json"
    return file_path.exists()


def get_missing_dates(data_dir, category, start_year, end_year):
    """
    Get list of missing dates that need to be crawled

    Args:
        data_dir: Base data directory
        category: News category
        start_year: Start year
        end_year: End year

    Returns:
        list: List of (year, month) tuples that need crawling
    """
    missing_months = []
    now = datetime.now()

    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            # Skip future months
            if year == now.year and month > now.month:
                continue

            # Check if any file exists for this month
            first_day = f"{year}-{month:02d}-01"

            if not check_file_exists(data_dir, category, first_day):
                missing_months.append((year, month))

    return missing_months


def crawl_month(crawler, category, year, month):
    """
    Crawl news for a specific month

    Args:
        crawler: CnyesCrawler instance
        category: News category
        year: Year
        month: Month

    Returns:
        dict: Statistics (news_count, days_count)
    """
    # Calculate start and end dates
    start_date = f"{year}-{month:02d}-01"

    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)

    last_day = (next_month - timedelta(days=1)).day
    end_date = f"{year}-{month:02d}-{last_day:02d}"

    print(f"\n{year}/{month:02d}: {start_date} ~ {end_date}")
    print("-" * 60)

    try:
        # Crawl news
        news = crawler.get_all_news(
            start_date=start_date,
            end_date=end_date,
            category=category,
            max_pages=None,
            delay=0.5
        )

        if news:
            # Save by date
            stats = crawler.save_news_by_date(news, data_type=f"raw_{category}")

            news_count = len(news)
            days_count = len(stats)

            print(f"✓ {year}/{month:02d}: {news_count} articles, {days_count} days")
            return {'news_count': news_count, 'days_count': days_count}
        else:
            print(f"⚠ {year}/{month:02d}: No news found")
            return {'news_count': 0, 'days_count': 0}

    except Exception as e:
        print(f"✗ {year}/{month:02d}: Error - {e}")
        return {'news_count': 0, 'days_count': 0, 'error': str(e)}


def main():
    parser = argparse.ArgumentParser(description='Crawl news from cnyes.com')
    parser.add_argument('--category', type=str, default='tw_stock',
                        choices=['tw_stock', 'us_stock'],
                        help='News category (default: tw_stock)')
    parser.add_argument('--start', type=int, help='Start year')
    parser.add_argument('--end', type=int, help='End year')
    parser.add_argument('--data-dir', type=str, default='data',
                        help='Data directory (default: data)')
    parser.add_argument('--force', action='store_true',
                        help='Force re-crawl existing data')

    args = parser.parse_args()

    # Get default years from config
    config = CATEGORY_CONFIG.get(args.category, {})
    start_year = args.start or config.get('default_start', 2015)
    end_year = args.end or config.get('default_end', datetime.now().year)

    print("╔" + "="*78 + "╗")
    print("║" + " "*25 + "News Crawler" + " "*25 + "║")
    print("╚" + "="*78 + "╝")
    print()
    print(f"Category: {args.category} ({config.get('name', 'Unknown')})")
    print(f"Time range: {start_year} - {end_year}")
    print(f"Data directory: {args.data_dir}")
    print(f"Resume mode: {'Disabled (--force)' if args.force else 'Enabled'}")
    print()

    # Initialize crawler
    crawler = CnyesCrawler(data_dir=args.data_dir)

    # Get missing months or all months (if --force)
    if args.force:
        print("Force mode: Re-crawling all months")
        missing_months = [(year, month)
                         for year in range(start_year, end_year + 1)
                         for month in range(1, 13)
                         if year < datetime.now().year or month <= datetime.now().month]
    else:
        missing_months = get_missing_dates(args.data_dir, args.category, start_year, end_year)

        if not missing_months:
            print("✓ All months already crawled! Nothing to do.")
            print("\nUse --force to re-crawl existing data.")
            return

        print(f"Found {len(missing_months)} months to crawl")

    # Confirm before starting
    if len(missing_months) > 0:
        print(f"\nWill crawl {len(missing_months)} months. Continue? (y/n): ", end='')
        if input().lower() != 'y':
            print("Cancelled")
            return

    # Statistics
    total_news = 0
    total_days = 0
    failed_months = []

    # Crawl missing months
    print("\n" + "="*80)
    print("Starting crawl...")
    print("="*80)

    for i, (year, month) in enumerate(missing_months, 1):
        print(f"\nProgress: {i}/{len(missing_months)}")

        result = crawl_month(crawler, args.category, year, month)

        total_news += result.get('news_count', 0)
        total_days += result.get('days_count', 0)

        if 'error' in result:
            failed_months.append(f"{year}/{month:02d}")

        # Small delay between months
        time.sleep(1)

    # Final summary
    print("\n" + "="*80)
    print("Completed!")
    print("="*80)
    print(f"\nTotal months: {len(missing_months)}")
    print(f"Total articles: {total_news:,}")
    print(f"Total days: {total_days:,}")

    if failed_months:
        print(f"\nFailed months ({len(failed_months)}):")
        for month in failed_months:
            print(f"  - {month}")
    else:
        print("\n✓ All months crawled successfully!")

    # Save summary
    summary = {
        "category": args.category,
        "start_year": start_year,
        "end_year": end_year,
        "total_months": len(missing_months),
        "total_news": total_news,
        "total_days": total_days,
        "failed_months": failed_months,
        "completed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    summary_dir = Path(args.data_dir)
    summary_dir.mkdir(exist_ok=True)
    summary_file = summary_dir / f"crawl_summary_{args.category}_{start_year}_{end_year}.json"

    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\nSummary saved to: {summary_file}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
