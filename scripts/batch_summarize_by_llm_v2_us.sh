#!/bin/bash
# Batch summarize trading day news with LLM for DJIA component stocks (30 stocks)

STOCKS=(
    AAPL   # Apple
    AMGN   # Amgen
    AMZN   # Amazon
    AXP    # American Express
    BA     # Boeing
    CAT    # Caterpillar
    CRM    # Salesforce
    CSCO   # Cisco Systems
    CVX    # Chevron
    DIS    # Walt Disney
    GS     # Goldman Sachs
    HD     # The Home Depot
    HON    # Honeywell International
    IBM    # IBM
    JNJ    # Johnson & Johnson
    JPM    # JPMorgan Chase
    KO     # Coca-Cola
    MCD    # McDonald's
    MMM    # 3M
    MRK    # Merck
    MSFT   # Microsoft
    NKE    # Nike
    NVDA   # NVIDIA
    PG     # Procter & Gamble
    SHW    # Sherwin-Williams
    TRV    # Travelers
    UNH    # UnitedHealth Group
    V      # Visa
    VZ     # Verizon
    WMT    # Walmart
)

START_DATE="2013-01-01"
END_DATE="2025-12-31"

WORKERS=4  # Parallel workers for faster processing

for stock in "${STOCKS[@]}"; do
    echo "Summarizing $stock..."
    python scripts/summarize_by_llm_v2.py --stock "$stock" --category us_stock --start "$START_DATE" --end "$END_DATE" --workers "$WORKERS"
done

echo "Done!"
