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
    trading_day_dir = Path(data_dir) / "stocks" / category / "by_trading_day" / stock_code

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
                content = article.get('extracted_content', '')
                total_tokens += count_tokens(content, encoder)

            data.append({
                'date': datetime.strptime(trading_day, '%Y-%m-%d'),
                'news_count': news_count,
                'total_tokens': total_tokens,
                'file': json_file.name
            })

        except Exception as e:
            print(f"Error loading {json_file}: {e}")

    return data


def compute_statistics(data: list, threshold: int, model: str) -> dict:
    """Compute summary statistics and return as dict"""
    if not data:
        return {}

    news_counts = [d['news_count'] for d in data]
    total_tokens = [d['total_tokens'] for d in data]

    # Basic stats
    total_days = len(data)
    days_with_news = len([c for c in news_counts if c > 0])
    zero_news_days = [d for d in data if d['news_count'] == 0]
    high_volume_days = [d for d in data if d['news_count'] > threshold]

    # Cost estimate
    total_token_sum = sum(total_tokens)
    input_cost = total_token_sum * 0.15 / 1_000_000 if model == "gpt-4o-mini" else 0

    return {
        'total_trading_days': total_days,
        'date_range_start': data[0]['date'].strftime('%Y-%m-%d'),
        'date_range_end': data[-1]['date'].strftime('%Y-%m-%d'),
        'token_model': model,
        'news_count': {
            'min': min(news_counts),
            'max': max(news_counts),
            'avg': sum(news_counts) / len(news_counts),
            'total': sum(news_counts),
        },
        'token_count': {
            'min': min(total_tokens),
            'max': max(total_tokens),
            'avg': sum(total_tokens) / len(total_tokens),
            'total': total_token_sum,
        },
        'days_with_news': days_with_news,
        'days_with_news_pct': days_with_news / total_days * 100,
        'days_without_news': len(zero_news_days),
        'days_without_news_pct': len(zero_news_days) / total_days * 100,
        'high_volume_days': len(high_volume_days),
        'high_volume_days_pct': len(high_volume_days) / total_days * 100,
        'threshold': threshold,
        'estimated_input_cost': input_cost,
        'zero_news_dates': [d['date'].strftime('%Y-%m-%d') for d in zero_news_days],
        'high_volume_details': [
            {'date': d['date'].strftime('%Y-%m-%d'), 'news_count': d['news_count'], 'tokens': d['total_tokens']}
            for d in sorted(high_volume_days, key=lambda x: x['news_count'], reverse=True)
        ],
    }


def print_statistics(data: list, threshold: int, model: str):
    """Print summary statistics"""
    stats = compute_statistics(data, threshold, model)
    if not stats:
        return

    print("=" * 60)
    print("Summary Statistics")
    print("=" * 60)
    print(f"Total trading days: {stats['total_trading_days']}")
    print(f"Date range: {stats['date_range_start']} ~ {stats['date_range_end']}")
    print(f"Token model: {stats['token_model']}")
    print()
    print("News count per day:")
    print(f"  Min: {stats['news_count']['min']}")
    print(f"  Max: {stats['news_count']['max']}")
    print(f"  Avg: {stats['news_count']['avg']:.1f}")
    print(f"  Total: {stats['news_count']['total']}")
    print()
    print("Token count per day (tiktoken):")
    print(f"  Min: {stats['token_count']['min']:,}")
    print(f"  Max: {stats['token_count']['max']:,}")
    print(f"  Avg: {stats['token_count']['avg']:,.0f}")
    print(f"  Total: {stats['token_count']['total']:,}")
    print()
    print("Coverage:")
    print(f"  Days with news: {stats['days_with_news']} ({stats['days_with_news_pct']:.1f}%)")
    print(f"  Days without news: {stats['days_without_news']} ({stats['days_without_news_pct']:.1f}%)")
    print(f"  High volume days (>{threshold}): {stats['high_volume_days']} ({stats['high_volume_days_pct']:.1f}%)")
    print()

    if stats['estimated_input_cost'] > 0:
        print(f"Estimated input cost (gpt-4o-mini): ${stats['estimated_input_cost']:.4f}")
        print()

    if stats['high_volume_details']:
        print(f"Days with > {threshold} news articles:")
        print("-" * 60)
        for d in stats['high_volume_details']:
            print(f"  {d['date']}: {d['news_count']} articles, {d['tokens']:,} tokens")
    else:
        print(f"No days exceed threshold of {threshold} articles.")

    print()
    if stats['zero_news_dates']:
        print(f"Days with 0 news articles ({len(stats['zero_news_dates'])} days):")
        print("-" * 60)
        for date in stats['zero_news_dates']:
            print(f"  {date}")
    else:
        print("All trading days have at least 1 news article.")


def save_statistics(stats: dict, output_path: Path):
    """Save statistics to a text file"""
    if not stats:
        return

    lines = [
        "=" * 60,
        "News Analysis Statistics",
        "=" * 60,
        "",
        "Basic Info",
        "-" * 40,
        f"Total trading days: {stats['total_trading_days']}",
        f"Date range: {stats['date_range_start']} ~ {stats['date_range_end']}",
        f"Token model: {stats['token_model']}",
        "",
        "News Count Per Day",
        "-" * 40,
        f"Min: {stats['news_count']['min']}",
        f"Max: {stats['news_count']['max']}",
        f"Avg: {stats['news_count']['avg']:.2f}",
        f"Total: {stats['news_count']['total']}",
        "",
        "Token Count Per Day",
        "-" * 40,
        f"Min: {stats['token_count']['min']:,}",
        f"Max: {stats['token_count']['max']:,}",
        f"Avg: {stats['token_count']['avg']:,.0f}",
        f"Total: {stats['token_count']['total']:,}",
        "",
        "Coverage",
        "-" * 40,
        f"Days with news: {stats['days_with_news']} / {stats['total_trading_days']} ({stats['days_with_news_pct']:.1f}%)",
        f"Days without news: {stats['days_without_news']} / {stats['total_trading_days']} ({stats['days_without_news_pct']:.1f}%)",
        f"High volume days (>{stats['threshold']}): {stats['high_volume_days']} / {stats['total_trading_days']} ({stats['high_volume_days_pct']:.1f}%)",
        "",
    ]

    if stats['estimated_input_cost'] > 0:
        lines.extend([
            "Cost Estimate",
            "-" * 40,
            f"Estimated input cost (gpt-4o-mini): ${stats['estimated_input_cost']:.4f}",
            "",
        ])

    if stats['high_volume_details']:
        lines.extend([
            f"High Volume Days (>{stats['threshold']} articles)",
            "-" * 40,
        ])
        for d in stats['high_volume_details']:
            lines.append(f"{d['date']}: {d['news_count']} articles, {d['tokens']:,} tokens")
        lines.append("")

    if stats['zero_news_dates']:
        lines.extend([
            f"Days Without News ({len(stats['zero_news_dates'])} days)",
            "-" * 40,
        ])
        for date in stats['zero_news_dates']:
            lines.append(date)
        lines.append("")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"Statistics saved to: {output_path}")


def save_statistics_json(stats: dict, output_path: Path):
    """Save statistics to a JSON file"""
    if not stats:
        return

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"Statistics JSON saved to: {output_path}")


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

    # Compute and print statistics
    stats = compute_statistics(data, args.threshold, args.model)
    print_statistics(data, args.threshold, args.model)

    # Create output directory
    output_dir = Path(args.data_dir) / "stocks" / args.category / "analysis" / args.stock
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save statistics to files
    stats_path = output_dir / "statistics.txt"
    save_statistics(stats, stats_path)

    stats_json_path = output_dir / "statistics.json"
    save_statistics_json(stats, stats_json_path)

    # Generate chart
    if not args.no_plot:
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
