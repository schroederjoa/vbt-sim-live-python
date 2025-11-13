# vbt-sim-live-python
Concept to implement vbt pro indicators and strategies that can be used for both simulation and live trading

## Background
Using [VectorBT PRO](https://vectorbt.pro/) now for approximately two years to backtest my trading strategies. At the same time, I am trading live on smaller timeframes such as 1m,2m and 5m. While the vbt framework is amazing to work with and fast for batch-processing large amounts of data, it did not give me the single-run execution time that I needed for quick order placement after getting a trigger signal. Not talking institutional HFT latencies, but I noticed that it does matter for my trading whether it takes 100ms for an order to be sent out or 2 seconds. This project is basically a concept for implementing indicators and strategies as vbt.IFs so they can be used identically in live trading and simulation. Perhaps it is helpful for some of you or provides ideas for your custom implementation.

## Notes
1. The general idea is to mainly work on fixed size numpy arrays, stored in LiveData.data, instead of vbt.data, to run fast updates
2. data that is used to initially populate the LiveData class (from_df() or prepare()) will determine the length of the numpy arrays
3. LiveData will provide methods for resampling, realignment and updates.
4. standard OHCLV has additional data fields "cpl" (to indicate whether a candle is complete or "in progress") and "date_l" (to store the latest date this candle was updated vs. the "date" which is more like an id of that candle)
5. strategies are implemented as IF with mandatory fields such as size, limit, stop, stoploss, ..
6. 1m source data (and updates) will be used to calculate and update higher intraday timeframes, where 1d source data is used for 1d and higher (weekly, monthly)

## Run examples
You will need a [VectorBT PRO](https://vectorbt.pro/) installation. Check [pyproject.toml](pyproject.toml) for further dependencies. Read the description in [examples/Test_VBT_Minute.py](examples/Test_VBT_Minute.py) and run it as either simulation or live example.
