#!/usr/bin/env python3
"""
Quick debug script to see what safe_download() returns
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from data.databento_safe_download import safe_download

print("Calling safe_download()...")
data = safe_download(
    dataset="GLBX.MDP3",
    symbols="ES.v.0",
    schema="ohlcv-1M",
    start="2025-09-01",
    end="2025-09-30",
    max_cost=5.0,
)

print(f"\nType of returned data: {type(data)}")
print(f"Data object: {data}")
print(f"\nAvailable attributes:")
print([attr for attr in dir(data) if not attr.startswith("_")])

print(f"\nTrying to convert:")
if hasattr(data, "to_df"):
    print("  ✓ Has .to_df() method")
    df = data.to_df()
    print(f"    Result type: {type(df)}")
elif hasattr(data, "data"):
    print("  ✓ Has .data attribute")
    print(f"    Type of .data: {type(data.data)}")
else:
    print("  ✗ No to_df() or .data attribute")

    # Check if it's already a DataFrame
    import pandas as pd

    if isinstance(data, pd.DataFrame):
        print("  ✓ Already a DataFrame!")
    else:
        print(f"  ? Unknown type: {type(data)}")
