#!/bin/bash
# Batch summarize trading day news with LLM (one sentence) for DJIA component stocks (29 stocks)

STOCKS=(
    UNH    # UnitedHealth Group
    GS     # Goldman Sachs
    MSFT   # Microsoft
    HD     # The Home Depot
    CAT    # Caterpillar
    AMGN   # Amgen
    MCD    # McDonald's
    CRM    # Salesforce.com
    V      # Visa
    AXP    # American Express
    TRV    # Travelers
    AAPL   # Apple
    JPM    # JPMorgan Chase
    IBM    # IBM
    HON    # Honeywell International
    AMZN   # Amazon
    PG     # Procter & Gamble
    JNJ    # Johnson & Johnson
    BA     # Boeing
    CVX    # Chevron
    MMM    # 3M
    MRK    # Merck Sharp & Dohme
    DIS    # Walt Disney
    WMT    # Walmart Inc
    NKE    # Nike
    KO     # Coca-Cola
    CSCO   # Cisco Systems
    VZ     # Verizon
    INTC   # Intel
)

START_DATE="2013-01-01"
END_DATE="2025-12-31"

WORKERS=4  # Parallel workers for faster processing

for stock in "${STOCKS[@]}"; do
    echo "Summarizing $stock..."
    python scripts/summarize_by_llm_v2.py --stock "$stock" --category us_stock --start "$START_DATE" --end "$END_DATE" --workers "$WORKERS"
done

echo "Done!"
