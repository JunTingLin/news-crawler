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


# TWII 50 stocks list (48 stocks)
# Format: "stock_code": (include_list, exclude_list)
# - include_list: keywords to match (OR logic)
# - exclude_list: keywords to exclude (OR logic), use [] if none
# Match logic: (A OR B) AND NOT (C OR D)
TWII_STOCKS = {
    "0050": (["0050", "元大台灣50", "元大50", "台灣50", "加權指數"], []),  # 元大台灣50 ETF / 大盤指數
    "1216": (["統一企業", "統一(1216", "1216-TW"], ["統一超", "統一發票"]),  # 統一企業
    "1301": (["台塑"], ["台塑化"]),           # 台塑，排除台塑化
    "1303": (["南亞"], ["南亞科"]),           # 南亞塑膠，排除南亞科
    "2002": (["中鋼"], []),
    "2059": (["川湖"], []),
    "2207": (["和泰車"], []),
    "2301": (["光寶科"], []),
    "2303": (["聯電"], []),
    "2308": (["台達電"], []),
    "2317": (["鴻海"], []),
    "2327": (["國巨"], []),
    "2330": (["台積電"], []),
    "2345": (["智邦"], []),
    "2357": (["華碩"], []),
    "2360": (["致茂"], []),
    "2379": (["瑞昱"], []),
    "2382": (["廣達"], []),
    "2383": (["台光電"], []),
    "2395": (["研華"], []),
    "2408": (["南亞科"], []),
    "2412": (["中華電"], []),
    "2454": (["聯發科"], []),
    "2603": (["長榮"], ["長榮航"]),           # 長榮海運，排除長榮航空
    "2615": (["萬海"], []),
    "2880": (["華南金"], []),
    "2881": (["富邦金"], []),
    "2882": (["國泰金"], []),
    "2883": (["凱基金", "開發金"], []),
    "2884": (["玉山金"], []),
    "2885": (["元大金"], []),
    "2886": (["兆豐金"], []),
    "2887": (["台新金", "新光金"], []),
    "2890": (["永豐金"], []),
    "2891": (["中信金"], []),
    "2892": (["第一金"], []),
    "2912": (["統一超"], []),
    "3008": (["大立光"], []),
    "3017": (["奇鋐"], []),
    "3034": (["聯詠"], []),
    "3045": (["台灣大"], []),
    "3231": (["緯創"], []),
    "3653": (["健策"], []),
    "3661": (["世芯"], []),
    "3665": (["貿聯"], []),
    "4904": (["遠傳"], []),
    "5880": (["合庫金"], []),
    "6505": (["台塑化"], []),
}

# DJIA 30 stocks (as of 2024)
# Format: "stock_code": (include_list, exclude_list)
# Using company names + ticker-US format for precision
US_STOCKS = {
    "AAPL": (["Apple", "蘋果", "AAPL-US"], []),
    "AMGN": (["Amgen", "安進", "AMGN-US"], []),
    "AMZN": (["Amazon", "亞馬遜", "AMZN-US"], []),
    "AXP": (["American Express", "美國運通", "AXP-US"], []),
    "BA": (["Boeing", "波音", "BA-US"], []),
    "CAT": (["Caterpillar", "開拓重工", "卡特彼勒", "CAT-US"], []),
    "CRM": (["Salesforce", "賽富時", "CRM-US"], []),
    "CSCO": (["Cisco", "思科", "CSCO-US"], []),
    "CVX": (["Chevron", "雪佛龍", "CVX-US"], []),
    "DIS": (["Disney", "迪士尼", "DIS-US"], []),
    "GS": (["Goldman Sachs", "高盛", "GS-US"], []),
    "HD": (["Home Depot", "家得寶", "HD-US"], []),
    "HON": (["Honeywell", "漢威聯合", "霍尼韋爾", "HON-US"], []),
    "IBM": (["IBM", "IBM-US"], []),
    "JNJ": (["Johnson & Johnson", "嬌生", "JNJ-US"], []),
    "JPM": (["JPMorgan", "摩根大通", "JPM-US"], []),
    "KO": (["Coca-Cola", "可口可樂", "KO-US"], []),
    "MCD": (["McDonald", "麥當勞", "MCD-US"], []),
    "MMM": (["3M", "MMM-US"], []),
    "MRK": (["Merck", "默克", "默沙東", "MRK-US"], []),
    "MSFT": (["Microsoft", "微軟", "MSFT-US"], []),
    "NKE": (["Nike", "耐吉", "耐克", "NKE-US"], []),
    "NVDA": (["NVIDIA", "輝達", "NVDA-US"], []),
    "PG": (["Procter & Gamble", "寶僑", "P&G", "PG-US"], []),
    "SHW": (["Sherwin-Williams", "宣偉", "SHW-US"], []),
    "TRV": (["Travelers", "旅行家", "TRV-US"], []),
    "UNH": (["UnitedHealth", "聯合健康", "UNH-US"], []),
    "V": (["Visa", "威士卡", "V-US"], []),
    "VZ": (["Verizon", "威瑞森", "VZ-US"], []),
    "WMT": (["Walmart", "沃爾瑪", "WMT-US"], []),
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
        keywords_tuple = stock_list[stock_code]
        include_list, exclude_list = keywords_tuple
        keywords_str = ', '.join(include_list)
        if exclude_list:
            keywords_str += f" (excl: {', '.join(exclude_list)})"
        print(f"  {stock_code:6s} {keywords_str:30s}: {count:5,} articles")

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
