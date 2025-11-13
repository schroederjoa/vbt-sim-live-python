#!/usr/bin/env python3
"""
Check what the Databento Parquet file actually contains
"""

import pandas as pd

print("Loading ES Parquet file...")
df = pd.read_parquet("data/raw/ES_ohlcv_1m.parquet")

print(f"\nDataFrame shape: {df.shape}")
print(f"\nColumn names: {list(df.columns)}")
print(f"\nIndex name: {df.index.name}")
print(f"\nIndex type: {type(df.index)}")
print(f"\nFirst few rows:")
print(df.head())
print(f"\nDataFrame info:")
print(df.info())
print(f"\nDataFrame dtypes:")
print(df.dtypes)
