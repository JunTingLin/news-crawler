#!/usr/bin/env python3
"""統計指定股票每年的新聞數量"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def count_news_by_year(stock_id: str, start_year: int = 2015, end_year: int = 2025):
    """統計指定股票每年的新聞數量

    Args:
        stock_id: 股票代碼
        start_year: 起始年份
        end_year: 結束年份

    Returns:
        dict: {year: count}
    """
    json_file = Path(f"data/stocks/tw_stock/{stock_id}/201601_202512.json")

    if not json_file.exists():
        print(f"找不到文件: {json_file}")
        return {}

    # 初始化每年的計數器
    year_counts = defaultdict(int)

    # 讀取並統計
    with open(json_file, 'r', encoding='utf-8') as f:
        news_list = json.load(f)

    for news in news_list:
        # 解析日期
        date_str = news.get('publish_time', '')
        try:
            # 日期格式: YYYY-MM-DD HH:MM:SS
            if date_str:
                year = None
                if len(date_str) >= 4:
                    year_str = date_str[:4]
                    if year_str.isdigit():
                        year = int(year_str)

                if year and start_year <= year <= end_year:
                    year_counts[year] += 1
        except Exception as e:
            print(f"日期解析錯誤: {date_str}, 錯誤: {e}")
            continue

    return dict(sorted(year_counts.items()))


def main():
    stocks = ['5880', '2330']
    start_year = 2015
    end_year = 2025

    print(f"統計期間: {start_year}-01-01 至 {end_year}-12-31")
    print("=" * 70)

    for stock_id in stocks:
        print(f"\n股票代碼: {stock_id}")
        print("-" * 70)

        year_counts = count_news_by_year(stock_id, start_year, end_year)

        if not year_counts:
            print("無數據")
            continue

        total = 0
        for year in range(start_year, end_year + 1):
            count = year_counts.get(year, 0)
            total += count
            print(f"{year}: {count:6,} 篇")

        print("-" * 70)
        print(f"總計: {total:6,} 篇")
        print("=" * 70)


if __name__ == "__main__":
    main()
