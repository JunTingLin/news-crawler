#!/bin/bash
# Batch analyze trading day for DJIA component stocks (30 stocks)

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

for stock in "${STOCKS[@]}"; do
    echo "Analyzing $stock..."
    python scripts/analyze_trading_day.py --stock "$stock" --category us_stock
done

echo "Done!"
