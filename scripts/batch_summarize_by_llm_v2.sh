#!/bin/bash
# Batch summarize trading day news with LLM (one sentence) for TWII component stocks (29 stocks)

STOCKS=(
    1216  # 統一
    1301  # 台塑
    1303  # 南亞
    2002  # 中鋼
    2303  # 聯電
    2308  # 台達電
    2317  # 鴻海
    2330  # 台積電
    2357  # 華碩
    2382  # 廣達
    2395  # 研華
    2412  # 中華電
    2454  # 聯發科
    2880  # 華南金
    2881  # 富邦金
    2882  # 國泰金
    2884  # 玉山金
    2885  # 元大金
    2886  # 兆豐金
    2887  # 台新新光金
    2891  # 中信金
    2892  # 第一金
    2912  # 統一超
    3008  # 大立光
    3045  # 台灣大
    3711  # 日月光投控
    4904  # 遠傳
    5880  # 合庫金
    6505  # 台塑化
)

START_DATE="2016-01-01"
END_DATE="2025-12-31"

for stock in "${STOCKS[@]}"; do
    echo "Summarizing $stock..."
    python scripts/summarize_by_llm_v2.py --stock "$stock" --start "$START_DATE" --end "$END_DATE"
done

echo "Done!"
