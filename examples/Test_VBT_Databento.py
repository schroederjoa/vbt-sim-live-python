"""
Backtest with real Databento CME futures data (ES - E-mini S&P 500).

This is identical to Test_VBT_Minute.py, but uses real data from Databento
instead of test data.

Run this to verify the complete pipeline works end-to-end.
"""

import time
from datetime import datetime

import _setpath
import pandas as pd
import pytz

from vbt_sim_live import GenericData, LiveData, SimData, TFs

# Dictionary that holds information about which indicators should be
# used for a particular timeframe and its parameters
indicator_info = {
    "m1": {
        "IndicatorRSI": {"period": 14},
        "IndicatorBasic": {},
        "IndicatorMAs": {},
        "IndicatorVWAP": {},
    },
    "m5": {
        "IndicatorRSI": {"period": 14},
        "IndicatorBasic": {},
        "IndicatorMAs": {},
        "IndicatorVWAP": {},
    },
    "m30": {
        "IndicatorRSI": {"period": 14},
        "IndicatorBasic": {},
        "IndicatorMAs": {},
        "IndicatorVWAP": {},
    },
}

# Dictionary that holds information about which strategies should be
# used for a particular timeframe and its parameters
strategy_info = {
    "m1": {
        "StrategyRSI": {
            "threshold_high": 70,
            "threshold_low": 30,
            "order_type": "limit",
            "profit_rr": 3,
            "min_risk": 0.1,
            "risk_per_trade": 500,
        },
    },
}

# Dictionary that holds information about realignment
realign_info = [
    {"align": "close", "feature": "rsi", "from": "m5", "to": "m1"},
    {"align": "close", "feature": "s20", "from": "m5", "to": "m1"},
    {"align": "close", "feature": "s200", "from": "m5", "to": "m1"},
    {"align": "close", "feature": "s20", "from": "m30", "to": "m1"},
    {"align": "close", "feature": "s200", "from": "m30", "to": "m1"},
]


# Class to simulate data on a minute / intraday level
class TesterSim:
    def __init__(self):
        pass

    def run(self):
        print("Loading Databento ES data...")
        # Load Parquet file (the only difference from Test_VBT_Minute.py)
        df = pd.read_parquet("data/raw/ES_ohlcv_1m.parquet")

        print(f"Raw Parquet columns: {list(df.columns)}")
        print(f"Raw Parquet index: {df.index.name}")

        # Clean up Databento format:
        # 1. Keep only OHLCV columns
        df = df[["open", "high", "low", "close", "volume"]].copy()

        # 2. Reset index so ts_event becomes a column named 'date'
        df = df.reset_index()
        df = df.rename(columns={"ts_event": "date"})

        # 3. Ensure correct format (handles timezone, cpl, date_l, and sets date as index)
        df = GenericData.df_ensure_format(df)

        symbol = "ES"

        # Dictionary to hold all our data classes with timeframe as key
        sim_data = {}

        # Create ohlc data for timeframes of interest
        # m1 data is coming from the source, other timeframes are resampled from m1
        sim_data["m1"] = SimData.from_df(df, symbol, TFs["m1"], log_handler=print)
        sim_data["m5"] = sim_data["m1"].resample(TFs["m5"])
        sim_data["m30"] = sim_data["m1"].resample(TFs["m30"])

        # Set and prepare indicators for timeframes
        sim_data["m1"].set_indicators(indicator_info)
        sim_data["m1"].prepare_indicators()

        sim_data["m5"].set_indicators(indicator_info)
        sim_data["m5"].prepare_indicators()

        sim_data["m30"].set_indicators(indicator_info)
        sim_data["m30"].prepare_indicators()

        # Realign indicators
        sim_data["m1"].realign(sim_data["m5"], realign_info)
        sim_data["m1"].realign(sim_data["m30"], realign_info)

        # Set and calculate strategies
        sim_data["m1"].set_strategies(strategy_info)
        sim_data["m1"].prepare_strategies()

        # Define simulation parameters
        # Using a 1-month window for faster testing
        simulation_parameters = {
            "start": pytz.timezone("America/New_York").localize(
                datetime(2025, 9, 1, 0, 0, 0)
            ),
            "end": pytz.timezone("America/New_York").localize(
                datetime(2025, 9, 30, 23, 59, 0)
            ),
            "cash": 100000,
        }

        print(f"\nRunning simulation for {symbol}...")
        print(
            f"Date range: {simulation_parameters['start']} to {simulation_parameters['end']}"
        )
        print(f"Starting cash: ${simulation_parameters['cash']:,.2f}\n")

        # Simulate timeframe of interest on m1 data
        sim_data["m1"].simulate(simulation_parameters, sim_data["m1"])

        # Convert m5 data to DataFrame and display the results
        print("\nBacktest complete!")
        print("Saving results...")

        df = sim_data["m5"].to_df(tz_convert=True)
        print(df)

        output_file = "results/sim_data_m5_databento_es.csv"
        import os

        os.makedirs("results", exist_ok=True)
        df.to_csv(output_file)
        print(f"\n✓ Results saved to: {output_file}")


if __name__ == "__main__":
    t = TesterSim()
    t.run()
