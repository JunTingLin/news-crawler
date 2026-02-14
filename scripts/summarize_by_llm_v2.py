#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Summarize Trading Day News with LLM (V2 - One Sentence)

Uses OpenAI API to generate one-sentence daily news summaries.
Focuses on news directly related to the specific stock.

Usage:
    python scripts/summarize_by_llm_v2.py --stock 2330
    python scripts/summarize_by_llm_v2.py --stock 2330 --start 2024-01-01 --end 2024-01-31
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


SYSTEM_PROMPT_TEMPLATE = """你是一位專業的財經新聞編輯。你的任務是用一句話總結與 {stock_id} 直接相關的新聞重點。

規則：
1. 使用繁體中文
2. 只提取與 {stock_id} 直接相關的資訊（如：該公司的營收、產品、人事、合作、法說會等）
3. 忽略僅提及該股票代號但內容不相關的新聞
4. 輸出一句簡潔的事實陳述，不超過50字
5. 如果沒有與該股票直接相關的新聞，回覆「無」"""

USER_PROMPT_TEMPLATE = """以下是 {stock_code} 在 {trading_day} 的相關新聞標題：

{news_titles}

請用一句話總結與 {stock_code} 直接相關的新聞重點："""


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """Count tokens using tiktoken"""
    encoder = tiktoken.encoding_for_model(model)
    return len(encoder.encode(text))


def format_news_titles(news_list: list) -> str:
    """Format news titles for the prompt"""
    titles = []
    for article in news_list:
        title = article.get('title', '').strip()
        if title:
            titles.append(f"- {title}")
    return "\n".join(titles)


def summarize_trading_day(client: OpenAI, model: str, stock_code: str,
                          day_data: dict, max_tokens: int = 100) -> dict:
    """
    Summarize news for a single trading day with one sentence

    Returns:
        dict with summary and metadata
    """
    trading_day = day_data.get('trading_day')
    news_window = day_data.get('news_window', {})
    news_list = day_data.get('news', [])

    if not news_list:
        return {
            'trading_day': trading_day,
            'summary': '無',
            'news_count': 0,
            'input_tokens': 0,
            'output_tokens': 0
        }

    # Format news titles only (not full content)
    news_titles = format_news_titles(news_list)

    # Build system prompt with stock_id
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(stock_id=stock_code)

    # Build user prompt
    user_prompt = USER_PROMPT_TEMPLATE.format(
        stock_code=stock_code,
        trading_day=trading_day,
        news_titles=news_titles
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
    trading_day_dir = Path(data_dir) / "stocks" / category / "by_trading_day" / stock_code

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
    parser = argparse.ArgumentParser(description='Summarize trading day news with LLM (one sentence)')
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
    parser.add_argument('--max-tokens', type=int, default=100,
                        help='Max output tokens per summary (default: 100)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be processed without calling API')
    parser.add_argument('--force', action='store_true',
                        help='Force re-summarize existing files')

    args = parser.parse_args()

    print("=" * 60)
    print(f"LLM News Summarizer V2 (One Sentence) - {args.stock}")
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
        print("Please run split_by_trading_day_v2.py first.")
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
    output_dir = Path(args.data_dir) / "stocks" / args.category / "summaries_v2" / args.stock
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
            skipped += 1
            continue

        # Load trading day data
        with open(json_file, 'r', encoding='utf-8') as f:
            day_data = json.load(f)

        news_count = day_data.get('news_count', 0)
        print(f"  {json_file.stem}: {news_count} articles...", end=" ", flush=True)

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

            # Show summary inline
            summary = result.get('summary', '')
            if len(summary) > 40:
                summary = summary[:40] + "..."
            print(f"'{summary}'")

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
