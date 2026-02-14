#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze Trading Day News

Analyzes news distribution across trading days and generates visualization.
Helps identify days with unusual news volume before running LLM summarization.

Usage:
    python scripts/analyze_trading_day.py --stock 2330
    python scripts/analyze_trading_day.py --stock 2330 --threshold 15
"""

import sys
import os
import argparse
import json
from pathlib import Path
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import tiktoken


def get_encoder(model: str = "gpt-4o-mini"):
    """Get tiktoken encoder for the specified model"""
    return tiktoken.encoding_for_model(model)


def count_tokens(text: str, encoder) -> int:
    """Count tokens using tiktoken encoder"""
    return len(encoder.encode(text))


def load_trading_day_data(data_dir: str, category: str, stock_code: str, model: str = "gpt-4o-mini") -> list:
    """
    Load all trading day JSON files for a stock

    Returns:
        list: List of dicts with date, news_count, total_tokens
    """
    trading_day_dir = Path(data_dir) / "stocks" / category / stock_code / "by_trading_day"

    if not trading_day_dir.exists():
        print(f"Directory not found: {trading_day_dir}")
        print("Please run split_by_trading_day.py first.")
        return []

    # Initialize tiktoken encoder
    encoder = get_encoder(model)

    data = []

    for json_file in sorted(trading_day_dir.glob("*.json")):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                day_data = json.load(f)

            trading_day = day_data.get('trading_day')
            news_count = day_data.get('news_count', 0)
            news_list = day_data.get('news', [])

            # Calculate total tokens using tiktoken
            total_tokens = 0
            for article in news_list:
                title = article.get('title', '')
                content = article.get('content', '')
                total_tokens += count_tokens(title + content, encoder)

            data.append({
                'date': datetime.strptime(trading_day, '%Y-%m-%d'),
                'news_count': news_count,
                'total_tokens': total_tokens,
                'file': json_file.name
            })

        except Exception as e:
            print(f"Error loading {json_file}: {e}")

    return data


def print_statistics(data: list, threshold: int, model: str):
    """Print summary statistics"""
    if not data:
        return

    news_counts = [d['news_count'] for d in data]
    total_tokens = [d['total_tokens'] for d in data]

    print("=" * 60)
    print("Summary Statistics")
    print("=" * 60)
    print(f"Total trading days: {len(data)}")
    print(f"Date range: {data[0]['date'].strftime('%Y-%m-%d')} ~ {data[-1]['date'].strftime('%Y-%m-%d')}")
    print(f"Token model: {model}")
    print()
    print("News count per day:")
    print(f"  Min: {min(news_counts)}")
    print(f"  Max: {max(news_counts)}")
    print(f"  Avg: {sum(news_counts) / len(news_counts):.1f}")
    print(f"  Total: {sum(news_counts)}")
    print()
    print("Token count per day (tiktoken):")
    print(f"  Min: {min(total_tokens):,}")
    print(f"  Max: {max(total_tokens):,}")
    print(f"  Avg: {sum(total_tokens) / len(total_tokens):,.0f}")
    print(f"  Total: {sum(total_tokens):,}")
    print()

    # Cost estimate for gpt-4o-mini (input only)
    total_token_sum = sum(total_tokens)
    if model == "gpt-4o-mini":
        input_cost = total_token_sum * 0.15 / 1_000_000
        print(f"Estimated input cost (gpt-4o-mini): ${input_cost:.4f}")
        print()

    # Find days exceeding threshold
    high_volume_days = [d for d in data if d['news_count'] > threshold]

    if high_volume_days:
        print(f"Days with > {threshold} news articles:")
        print("-" * 60)
        for d in sorted(high_volume_days, key=lambda x: x['news_count'], reverse=True):
            print(f"  {d['date'].strftime('%Y-%m-%d')}: {d['news_count']} articles, {d['total_tokens']:,} tokens")
    else:
        print(f"No days exceed threshold of {threshold} articles.")

    # Find days with zero news
    zero_news_days = [d for d in data if d['news_count'] == 0]

    print()
    if zero_news_days:
        print(f"Days with 0 news articles ({len(zero_news_days)} days):")
        print("-" * 60)
        for d in sorted(zero_news_days, key=lambda x: x['date']):
            print(f"  {d['date'].strftime('%Y-%m-%d')}")
    else:
        print("All trading days have at least 1 news article.")


def plot_news_distribution(data: list, stock_code: str, output_path: Path, threshold: int):
    """Generate bar chart of news distribution"""
    if not data:
        return

    dates = [d['date'] for d in data]
    counts = [d['news_count'] for d in data]

    # Color bars based on threshold
    colors = ['red' if c > threshold else 'steelblue' for c in counts]

    fig, ax = plt.subplots(figsize=(14, 6))

    # Use index as x-axis (categorical) to avoid gaps for non-trading days
    x_positions = range(len(dates))
    ax.bar(x_positions, counts, color=colors, width=0.8)

    # Add threshold line
    ax.axhline(y=threshold, color='red', linestyle='--', linewidth=1, label=f'Threshold ({threshold})')

    # Formatting
    ax.set_xlabel('Trading Day')
    ax.set_ylabel('News Count')
    ax.set_title(f'News Distribution by Trading Day - {stock_code}')

    # Set x-axis labels to show month boundaries
    # Find indices where month changes
    month_labels = []
    month_positions = []
    prev_month = None
    for i, d in enumerate(dates):
        month_key = d.strftime('%Y-%m')
        if month_key != prev_month:
            month_labels.append(month_key)
            month_positions.append(i)
            prev_month = month_key

    ax.set_xticks(month_positions)
    ax.set_xticklabels(month_labels, rotation=45, ha='right')

    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f"Chart saved to: {output_path}")

    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Analyze trading day news distribution')
    parser.add_argument('--stock', type=str, required=True,
                        help='Stock code (e.g., 2330)')
    parser.add_argument('--category', type=str, default='tw_stock',
                        help='News category (default: tw_stock)')
    parser.add_argument('--data-dir', type=str, default='data',
                        help='Data directory (default: data)')
    parser.add_argument('--threshold', type=int, default=15,
                        help='Threshold for high volume warning (default: 15)')
    parser.add_argument('--model', type=str, default='gpt-4o-mini',
                        help='Model for token counting (default: gpt-4o-mini)')
    parser.add_argument('--no-plot', action='store_true',
                        help='Skip generating chart')

    args = parser.parse_args()

    print("=" * 60)
    print(f"Analyzing Trading Day News - {args.stock}")
    print("=" * 60)
    print()

    # Load data
    data = load_trading_day_data(args.data_dir, args.category, args.stock, args.model)

    if not data:
        print("No data found.")
        return

    # Print statistics
    print_statistics(data, args.threshold, args.model)

    # Generate chart
    if not args.no_plot:
        output_dir = Path(args.data_dir) / "stocks" / args.category / args.stock
        output_path = output_dir / "news_distribution.png"
        plot_news_distribution(data, args.stock, output_path, args.threshold)


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
