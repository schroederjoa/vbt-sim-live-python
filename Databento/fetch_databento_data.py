#!/usr/bin/env python3
"""
Fetch CME futures data from Databento and save as Parquet files.

This script:
1. Uses safe_download() to check cost before downloading
2. Fetches 1-minute OHLCV bars (included in Standard Plan)
3. Saves as Parquet (4-5x compression vs CSV)
4. Handles API key from .env file

Usage:
    python scripts/fetch_databento_data.py              # Fetch all symbols
    python scripts/fetch_databento_data.py ES           # Fetch only ES
    python scripts/fetch_databento_data.py ES NQ GC     # Fetch multiple
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path so we can import from data/
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from dotenv import load_dotenv

# Import the safe download wrapper
try:
    from data.databento_safe_download import safe_download
except ImportError:
    print("Error: Could not import safe_download from data/databento_safe_download.py")
    print("Make sure you've copied the file from your old project!")
    sys.exit(1)

# Load API key from .env
load_dotenv()
API_KEY = os.getenv("DATABENTO_API_KEY")

if not API_KEY:
    print("Error: DATABENTO_API_KEY not found in .env file")
    print("Please add: DATABENTO_API_KEY=db-YOUR_KEY_HERE")
    sys.exit(1)

# ============================================================================
# Configuration
# ============================================================================

SYMBOLS = {
    "ES": "ES.v.0",  # E-mini S&P 500
    "NQ": "NQ.v.0",  # E-mini NASDAQ
    "GC": "GC.v.0",  # Gold
    "ZB": "ZB.v.0",  # 10-Year Treasury
    "ZC": "ZC.v.0",  # Corn
    "ZS": "ZS.v.0",  # Soybeans
    "NG": "NG.v.0",  # Natural Gas
    "SI": "SI.v.0",  # Silver
    "YM": "YM.v.0",  # E-mini Dow
}

DATASET = "GLBX.MDP3"  # CME Globex
SCHEMA = "ohlcv-1M"  # 1-minute bars (pre-resampled by Databento)
START_DATE = "2020-01-01"
END_DATE = "2025-10-31"
MAX_COST_PER_SYMBOL = 5.0  # Stop if any single symbol would cost > $5

# ============================================================================
# Main Script
# ============================================================================


def format_file_size(size_bytes):
    """Convert bytes to human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def fetch_symbol(symbol_short, symbol_long):
    """Fetch a single symbol and save as Parquet."""

    print(f"\n{'=' * 60}")
    print(f"Fetching {symbol_short}...")
    print(f"{'=' * 60}")

    try:
        # Step 1: Check cost
        print(f"  Checking cost for {symbol_short}...")

        data = safe_download(
            dataset=DATASET,
            symbols=symbol_long,
            schema=SCHEMA,
            start=START_DATE,
            end=END_DATE,
            max_cost=MAX_COST_PER_SYMBOL,
        )

        if data is None:
            print(f"  ✗ Download cancelled by user")
            return False

        # Step 2: Save to Parquet
        # BentoData object has a built-in .to_parquet() method
        output_dir = Path("data/raw")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"{symbol_short}_ohlcv_1m.parquet"

        print(f"  Saving to Parquet...")
        data.to_parquet(str(output_file))

        # Step 3: Verify and report
        file_size = output_file.stat().st_size

        # Get number of rows from the underlying DataFrame
        # data.data is a symbol_dict, so get the first (and only) symbol
        df = list(data.data.values())[0]
        num_rows = len(df)

        print(f"  ✓ Success!")
        print(f"    File: {output_file}")
        print(f"    Size: {format_file_size(file_size)}")
        # Note: Rows represent 1-minute bars over the requested date range
        # ES trades ~23 hours/day (24h minus 1h maintenance), so ~1,380 bars/day
        print(f"    Rows: {num_rows:,} (1-minute bars from {START_DATE} to {END_DATE})")

        return True

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    """Main entry point."""

    print("\n" + "=" * 60)
    print("Databento CME Futures Data Fetcher")
    print("=" * 60)
    print(f"Dataset: {DATASET}")
    print(f"Schema: {SCHEMA} (1-minute bars)")
    print(f"Date Range: {START_DATE} to {END_DATE}")
    print(f"Max cost per symbol: ${MAX_COST_PER_SYMBOL}")

    # Parse command line arguments
    if len(sys.argv) > 1:
        # User specified symbols
        requested_symbols = sys.argv[1:]
        symbols_to_fetch = {k: v for k, v in SYMBOLS.items() if k in requested_symbols}

        if not symbols_to_fetch:
            print(f"\nError: No valid symbols provided")
            print(f"Available: {', '.join(SYMBOLS.keys())}")
            sys.exit(1)
    else:
        # Fetch all symbols
        symbols_to_fetch = SYMBOLS

    print(f"\nSymbols to fetch: {', '.join(symbols_to_fetch.keys())}")

    # Start fetching
    start_time = time.time()
    successful = []
    failed = []

    for symbol_short, symbol_long in symbols_to_fetch.items():
        if fetch_symbol(symbol_short, symbol_long):
            successful.append(symbol_short)
        else:
            failed.append(symbol_short)

    # Summary
    elapsed = time.time() - start_time

    print(f"\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"✓ Successful: {len(successful)} ({', '.join(successful)})")
    if failed:
        print(f"✗ Failed: {len(failed)} ({', '.join(failed)})")
    print(f"Time elapsed: {elapsed:.1f} seconds")
    print(f"\nData saved to: data/raw/")
    print(f"Ready to load into vbt-sim-live!")

    if not successful:
        sys.exit(1)


if __name__ == "__main__":
    main()
