name: Key Reversal Analysis

on:
  workflow_dispatch:  # permette avvio manuale

jobs:
  run-key-reversal:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pandas yfinance ta requests beautifulsoup4

      - name: Run Key Reversal Script
        run: |
          python data/key_reversal.py
