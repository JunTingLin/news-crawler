#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Summarize Trading Day News with LLM (V2 - One Sentence)

Uses Ollama API (OpenAI compatible) to generate one-sentence daily news summaries.
Supports parallel processing for faster execution.

Usage:
    python scripts/summarize_by_llm_v2.py --stock 2330
    python scripts/summarize_by_llm_v2.py --stock 2330 --start 2024-01-01 --end 2024-01-31
    python scripts/summarize_by_llm_v2.py --stock 2330 --workers 4
"""

import sys
import os
import argparse
import json
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from dotenv import load_dotenv
from openai import OpenAI

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.filter_stocks import TWII_STOCKS

# Load .env file
load_dotenv()

# Default Ollama endpoint
# Note for Ollama users: 172.18.48.1 is the Windows host IP from WSL
# Check with: ip route | grep default
DEFAULT_OLLAMA_URL = "http://172.18.48.1:11434/v1"
DEFAULT_MODEL = "qwen2.5:14b"


SYSTEM_PROMPT_TEMPLATE = """你是一位專業的財經新聞編輯。你的任務是用一句話總結與 {stock_name} 相關的新聞重點。

規則：
1. 使用繁體中文
2. 只提取與 {stock_name} 相關的資訊（如：該公司的營收、產品、人事、合作、法說會等）
3. 輸出一句簡潔的事實陳述，不超過100字
"""

USER_PROMPT_TEMPLATE = """以下是 {stock_name}({stock_code}) 在 {trading_day} 的相關新聞內容：

{news_content}

請用一句話總結與 {stock_name} 直接相關的新聞重點："""


def format_news_content(news_list: list, max_total_chars: int = 20000) -> str:
    """
    Format news content using pre-extracted content from split_by_trading_day_v2.

    Args:
        news_list: List of news articles (with extracted_content field)
        max_total_chars: Maximum total characters (to prevent context overflow)

    Returns:
        Formatted string with relevant snippets
    """
    contents = []
    total_chars = 0

    for article in news_list:
        # Use extracted_content (pre-computed by split_by_trading_day_v2.py)
        snippet = article.get('extracted_content', '').strip()

        # Fallback to summary if extracted_content is empty
        if not snippet:
            snippet = article.get('summary', '').strip()

        if not snippet:
            continue

        # Check total length limit
        if total_chars + len(snippet) > max_total_chars:
            remaining = max_total_chars - total_chars
            if remaining > 100:
                snippet = snippet[:remaining] + "...[truncated]"
                contents.append(f"- {snippet}")
            break

        contents.append(f"- {snippet}")
        total_chars += len(snippet)

    return "\n".join(contents)


def get_stock_name(stock_code: str) -> str:
    """Get stock name from TWII_STOCKS, fallback to stock_code"""
    if stock_code in TWII_STOCKS:
        include_list, _ = TWII_STOCKS[stock_code]
        return include_list[0] if include_list else stock_code
    return stock_code


def summarize_trading_day(client: OpenAI, model: str, stock_code: str,
                          day_data: dict, max_tokens: int = 100,
                          max_total_chars: int = 20000) -> dict:
    """
    Summarize news for a single trading day with one sentence

    Args:
        client: OpenAI client
        model: Model name
        stock_code: Stock code (e.g., '2330')
        day_data: Trading day data with news (must have extracted_content field)
        max_tokens: Max output tokens
        max_total_chars: Max total chars for input content

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
            'news_count': 0
        }

    # Get stock name
    stock_name = get_stock_name(stock_code)

    # Format news content (uses pre-extracted content from split_by_trading_day_v2)
    news_content = format_news_content(news_list, max_total_chars)

    # Build system prompt with stock_name
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(stock_name=stock_name)

    # Build user prompt
    user_prompt = USER_PROMPT_TEMPLATE.format(
        stock_name=stock_name,
        stock_code=stock_code,
        trading_day=trading_day,
        news_content=news_content
    )

    # Call Ollama API (OpenAI compatible)
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

    return {
        'trading_day': trading_day,
        'news_window': news_window,
        'news_count': len(news_list),
        'summary': summary,
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


def process_single_file(client: OpenAI, model: str, stock_code: str,
                        json_file: Path, output_dir: Path,
                        max_tokens: int, max_total_chars: int,
                        force: bool, print_lock: Lock) -> dict:
    """Process a single trading day file (for parallel execution)"""
    output_file = output_dir / json_file.name

    # Check if already summarized
    if output_file.exists() and not force:
        return {'status': 'skipped', 'file': json_file.name}

    # Load trading day data
    with open(json_file, 'r', encoding='utf-8') as f:
        day_data = json.load(f)

    news_count = day_data.get('news_count', 0)

    try:
        # Summarize
        result = summarize_trading_day(
            client, model, stock_code, day_data, max_tokens, max_total_chars
        )

        # Save result
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # Print progress (thread-safe)
        summary = result.get('summary', '')
        display_summary = summary[:40] + "..." if len(summary) > 40 else summary

        with print_lock:
            print(f"  {json_file.stem}: {news_count} articles -> '{display_summary}'")

        return {'status': 'processed', 'file': json_file.name, 'result': result}

    except Exception as e:
        with print_lock:
            print(f"  {json_file.stem}: error - {e}")
        return {'status': 'error', 'file': json_file.name, 'error': str(e)}


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
    parser.add_argument('--model', type=str, default=DEFAULT_MODEL,
                        help=f'LLM model (default: {DEFAULT_MODEL})')
    parser.add_argument('--ollama-url', type=str, default=DEFAULT_OLLAMA_URL,
                        help=f'Ollama API URL (default: {DEFAULT_OLLAMA_URL})')
    parser.add_argument('--max-tokens', type=int, default=100,
                        help='Max output tokens per summary (default: 100)')
    parser.add_argument('--max-total-chars', type=int, default=20000,
                        help='Max total chars for all articles (default: 20000)')
    parser.add_argument('--workers', type=int, default=1,
                        help='Number of parallel workers (default: 1)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be processed without calling API')
    parser.add_argument('--force', action='store_true',
                        help='Force re-summarize existing files')

    args = parser.parse_args()

    print("=" * 60)
    print(f"LLM News Summarizer V2 (Ollama) - {args.stock}")
    print("=" * 60)
    print()

    # Initialize Ollama client (OpenAI compatible)
    client = OpenAI(
        base_url=args.ollama_url,
        api_key="ollama"  # Ollama doesn't require a real API key
    )

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
    print(f"Ollama URL: {args.ollama_url}")
    print(f"Workers: {args.workers}")
    print(f"Max total chars: {args.max_total_chars}")
    print()

    if args.dry_run:
        print("[DRY RUN] Would process:")
        for f in files:
            print(f"  - {f.name}")
        return

    # Create output directory
    output_dir = Path(args.data_dir) / "stocks" / args.category / "summaries_v2" / args.stock
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process with parallel workers
    print_lock = Lock()
    processed = 0
    skipped = 0
    errors = 0

    if args.workers == 1:
        # Sequential processing
        for json_file in files:
            result = process_single_file(
                client, args.model, args.stock, json_file, output_dir,
                args.max_tokens, args.max_total_chars,
                args.force, print_lock
            )
            if result['status'] == 'processed':
                processed += 1
            elif result['status'] == 'skipped':
                skipped += 1
            else:
                errors += 1
    else:
        # Parallel processing
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(
                    process_single_file,
                    client, args.model, args.stock, json_file, output_dir,
                    args.max_tokens, args.max_total_chars,
                    args.force, print_lock
                ): json_file
                for json_file in files
            }

            for future in as_completed(futures):
                result = future.result()
                if result['status'] == 'processed':
                    processed += 1
                elif result['status'] == 'skipped':
                    skipped += 1
                else:
                    errors += 1

    # Summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Processed: {processed}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")
    print(f"Output directory: {output_dir}")


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
