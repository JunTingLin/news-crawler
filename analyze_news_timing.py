#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統計台股新聞在盤中和盤後發布的比例
"""
import json
from datetime import datetime
from collections import Counter

def categorize_news_time(publish_time_str):
    """
    根據發布時間判斷是盤中還是盤後

    台灣股市時間：
    - 盤中: 09:00-13:30
    - 盤後交易: 14:00-14:30
    - 其他時間: 收盤後

    Args:
        publish_time_str: 發布時間字串，格式如 "2016-01-04 21:08:34"

    Returns:
        str: "盤中" 或 "盤後"
    """
    try:
        dt = datetime.strptime(publish_time_str, "%Y-%m-%d %H:%M:%S")
        hour = dt.hour
        minute = dt.minute

        # 盤中時間: 09:00-13:30
        if (hour == 9 and minute >= 0) or (10 <= hour <= 12) or (hour == 13 and minute <= 30):
            return "盤中"
        else:
            return "盤後"
    except Exception as e:
        print(f"解析時間錯誤: {publish_time_str}, 錯誤: {e}")
        return "未知"

def analyze_news_timing(json_file_path):
    """
    分析新聞發布時間的統計

    Args:
        json_file_path: JSON 檔案路徑
    """
    print(f"正在讀取檔案: {json_file_path}")

    with open(json_file_path, 'r', encoding='utf-8') as f:
        news_data = json.load(f)

    print(f"總共有 {len(news_data)} 則新聞")

    # 統計盤中/盤後
    timing_counter = Counter()
    hour_counter = Counter()

    for news in news_data:
        publish_time = news.get('publish_time', '')
        timing = categorize_news_time(publish_time)
        timing_counter[timing] += 1

        # 同時統計小時分布
        try:
            dt = datetime.strptime(publish_time, "%Y-%m-%d %H:%M:%S")
            hour_counter[dt.hour] += 1
        except:
            pass

    # 輸出結果
    print("\n" + "="*60)
    print("盤中 vs 盤後新聞統計")
    print("="*60)

    total = sum(timing_counter.values())
    for timing, count in timing_counter.most_common():
        percentage = (count / total) * 100
        print(f"{timing}: {count:,} 則 ({percentage:.2f}%)")

    print("\n" + "="*60)
    print("每小時新聞數量分布")
    print("="*60)

    for hour in sorted(hour_counter.keys()):
        count = hour_counter[hour]
        percentage = (count / total) * 100
        bar = "█" * int(percentage)
        marker = " [盤中]" if 9 <= hour <= 13 else ""
        print(f"{hour:02d}:00 | {count:6,} ({percentage:5.2f}%) {bar}{marker}")

    print("\n" + "="*60)

if __name__ == "__main__":
    json_file = "/mnt/d/Code/PythonProjects/news-crawler/data/stocks/tw_stock/2330/201601_202512.json"
    analyze_news_timing(json_file)
