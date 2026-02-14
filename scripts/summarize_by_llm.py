#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Summarize Trading Day News with LLM

Uses OpenAI API to generate daily news summaries for each trading day.

Usage:
    python scripts/summarize_by_llm.py --stock 2330
    python scripts/summarize_by_llm.py --stock 2330 --start 2024-01-01 --end 2024-01-31
"""

import sys
import os
import argparse
import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
import tiktoken

# Load .env file
load_dotenv()


SYSTEM_PROMPT_TEMPLATE = """你是一位專業的財經新聞編輯。你的任務是將多篇新聞整合成一段客觀的事實陳述，專注於 {stock_id} 相關的內容。

請遵循以下規則：
1. 使用繁體中文
2. 將所有新聞的事實整合成一個連貫的段落，重點放在與 {stock_id} 相關的資訊
3. 只陳述新聞中的事實，不加入個人觀點、評論或情感
4. 如果多篇新聞提到相同事件，合併陳述；如果有矛盾，並列呈現
5. 輸出為一到三個段落的純文字，不使用條列格式"""

USER_PROMPT_TEMPLATE = """以下是 {stock_code} 在 {trading_day} 交易日開盤前的相關新聞。
新聞時間範圍：{news_window_start} 至 {news_window_end}

請將這些新聞整合成客觀的事實陳述：

{news_content}

---
請輸出整合後的事實摘要："""


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """Count tokens using tiktoken"""
    encoder = tiktoken.encoding_for_model(model)
    return len(encoder.encode(text))


def format_news_for_prompt(news_list: list, max_chars_per_article: int = 500) -> str:
    """Format news articles for the prompt"""
    formatted = []

    for i, article in enumerate(news_list, 1):
        title = article.get('title', '').strip()
        content = article.get('content', '').strip()
        publish_time = article.get('publish_time', '')

        # Truncate content if too long
        if len(content) > max_chars_per_article:
            content = content[:max_chars_per_article] + "..."

        formatted.append(f"【新聞 {i}】({publish_time})\n標題：{title}\n內容：{content}")

    return "\n\n".join(formatted)


def summarize_trading_day(client: OpenAI, model: str, stock_code: str,
                          day_data: dict, max_tokens: int = 1000) -> dict:
    """
    Summarize news for a single trading day

    Returns:
        dict with summary and metadata
    """
    trading_day = day_data.get('trading_day')
    news_window = day_data.get('news_window', {})
    news_list = day_data.get('news', [])

    if not news_list:
        return {
            'trading_day': trading_day,
            'summary': '當日無相關新聞',
            'news_count': 0,
            'input_tokens': 0,
            'output_tokens': 0
        }

    # Format news content
    news_content = format_news_for_prompt(news_list)

    # Build system prompt with stock_id
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(stock_id=stock_code)

    # Build user prompt
    user_prompt = USER_PROMPT_TEMPLATE.format(
        stock_code=stock_code,
        trading_day=trading_day,
        news_window_start=news_window.get('start', ''),
        news_window_end=news_window.get('end', ''),
        news_content=news_content
    )

    # Count input tokens
    input_tokens = count_tokens(system_prompt + user_prompt, model)

    # Call OpenAI API
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=max_tokens,
        temperature=0.3
    )

    summary = response.choices[0].message.content.strip()
    output_tokens = response.usage.completion_tokens if response.usage else count_tokens(summary, model)

    return {
        'trading_day': trading_day,
        'news_window': news_window,
        'news_count': len(news_list),
        'summary': summary,
        'input_tokens': response.usage.prompt_tokens if response.usage else input_tokens,
        'output_tokens': output_tokens,
        'model': model
    }


def load_trading_day_files(data_dir: str, category: str, stock_code: str,
                           start_date: str = None, end_date: str = None) -> list:
    """Load trading day JSON files"""
    trading_day_dir = Path(data_dir) / "stocks" / category / stock_code / "by_trading_day"

    if not trading_day_dir.exists():
        return []

    files = []

    for json_file in sorted(trading_day_dir.glob("*.json")):
        # Parse date from filename
        date_str = json_file.stem  # e.g., "2024-01-02"

        # Filter by date range
        if start_date and date_str < start_date:
            continue
        if end_date and date_str > end_date:
            continue

        files.append(json_file)

    return files


def main():
    parser = argparse.ArgumentParser(description='Summarize trading day news with LLM')
    parser.add_argument('--stock', type=str, required=True,
                        help='Stock code (e.g., 2330)')
    parser.add_argument('--category', type=str, default='tw_stock',
                        help='News category (default: tw_stock)')
    parser.add_argument('--start', type=str,
                        help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str,
                        help='End date (YYYY-MM-DD)')
    parser.add_argument('--data-dir', type=str, default='data',
                        help='Data directory (default: data)')
    parser.add_argument('--model', type=str, default='gpt-4o-mini',
                        help='OpenAI model (default: gpt-4o-mini)')
    parser.add_argument('--max-tokens', type=int, default=1000,
                        help='Max output tokens per summary (default: 1000)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be processed without calling API')
    parser.add_argument('--force', action='store_true',
                        help='Force re-summarize existing files')

    args = parser.parse_args()

    print("=" * 60)
    print(f"LLM News Summarizer - {args.stock}")
    print("=" * 60)
    print()

    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables.")
        print("Please add it to your .env file.")
        sys.exit(1)

    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)

    # Load trading day files
    files = load_trading_day_files(
        args.data_dir, args.category, args.stock,
        args.start, args.end
    )

    if not files:
        print("No trading day files found.")
        print("Please run split_by_trading_day.py first.")
        return

    print(f"Found {len(files)} trading days to process")
    print(f"Model: {args.model}")
    print()

    if args.dry_run:
        print("[DRY RUN] Would process:")
        for f in files:
            print(f"  - {f.name}")
        return

    # Create output directory
    output_dir = Path(args.data_dir) / "stocks" / args.category / args.stock / "summaries"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process each trading day
    total_input_tokens = 0
    total_output_tokens = 0
    processed = 0
    skipped = 0

    for json_file in files:
        # Check if already summarized
        output_file = output_dir / json_file.name
        if output_file.exists() and not args.force:
            print(f"  {json_file.stem}: already exists, skipping")
            skipped += 1
            continue

        # Load trading day data
        with open(json_file, 'r', encoding='utf-8') as f:
            day_data = json.load(f)

        print(f"  {json_file.stem}: {day_data.get('news_count', 0)} articles...", end=" ", flush=True)

        try:
            # Summarize
            result = summarize_trading_day(
                client, args.model, args.stock, day_data, args.max_tokens
            )

            # Save result
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            total_input_tokens += result.get('input_tokens', 0)
            total_output_tokens += result.get('output_tokens', 0)
            processed += 1

            print(f"done ({result.get('input_tokens', 0)} + {result.get('output_tokens', 0)} tokens)")

        except Exception as e:
            print(f"error: {e}")

    # Summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Processed: {processed}")
    print(f"Skipped: {skipped}")
    print(f"Total input tokens: {total_input_tokens:,}")
    print(f"Total output tokens: {total_output_tokens:,}")
    print(f"Output directory: {output_dir}")

    # Cost estimate for gpt-4o-mini
    if args.model == "gpt-4o-mini":
        input_cost = total_input_tokens * 0.15 / 1_000_000
        output_cost = total_output_tokens * 0.6 / 1_000_000
        print(f"Estimated cost: ${input_cost + output_cost:.4f}")


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
