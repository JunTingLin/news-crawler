#!/bin/bash
# Batch analyze trading day for DJIA component stocks (29 stocks)

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

for stock in "${STOCKS[@]}"; do
    echo "Analyzing $stock..."
    python scripts/analyze_trading_day.py --stock "$stock" --category us_stock
done

echo "Done!"
