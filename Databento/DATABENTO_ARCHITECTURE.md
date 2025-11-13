# Databento Integration Architecture

System design documentation for Vector Bot's Databento integration, covering data flow, module responsibilities, and continuous contract handling.

---

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Diagram](#architecture-diagram)
- [Data Flow](#data-flow)
- [Module Responsibilities](#module-responsibilities)
- [Continuous Contract System](#continuous-contract-system)
- [Panama Adjustment Algorithm](#panama-adjustment-algorithm)
- [Caching Strategy](#caching-strategy)
- [Validation Pipeline](#validation-pipeline)
- [Error Handling](#error-handling)
- [Performance Considerations](#performance-considerations)

---

## System Overview

Vector Bot's Databento integration is designed as a multi-layer system that transforms raw tick data into backtest-ready continuous price series.

### Key Design Principles

1. **Loosely Coupled** - Each module has clear boundaries and minimal dependencies
2. **Cache-First** - Data downloaded once, reused indefinitely
3. **Validation-Driven** - Every step includes automated quality checks
4. **Fail-Fast** - Errors caught early, never propagate invalid data
5. **Parquet-Native** - Efficient storage and fast random access

### System Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                     │
│  - CLI Scripts (download, validate, update)                 │
│  - Python API (load_tick_data_from_cache)                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Orchestration Layer                       │
│  - tick_processor.process_symbol_bulk()                     │
│  - Coordinates: fetch → adjust → resample → validate        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Processing Layer                          │
│  - Data Fetching (databento_provider)                       │
│  - Adjustment (continuous_adjustment)                       │
│  - Resampling (tick_processor)                              │
│  - Validation (validation/tick_resampling)                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     Storage Layer                           │
│  - Parquet files (data_cache/)                              │
│  - Roll metadata (JSON)                                     │
│  - Validation reports (JSON)                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture Diagram

### Complete Data Pipeline

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         DATABENTO INTEGRATION                             │
└──────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│  Databento API  │  (External)
│   GLBX.MDP3     │
└────────┬────────┘
         │ HTTPS (tick data)
         ↓
┌─────────────────────────────────────────────────────────────┐
│                    databento_provider.py                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  fetch_tick_data_bulk()                              │   │
│  │  - Chunks: 6-month periods                           │   │
│  │  - Schema: 'trades' (tick data)                      │   │
│  │  - Symbol: 'ES.v.0' (volume-based continuous)        │   │
│  │  - Saves: data_cache/raw_ticks/*.parquet             │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  get_symbol_mapping_events()                         │   │
│  │  - Fetches: SymbolMappingMsg records                 │   │
│  │  - Detects: Roll dates (ESH5 → ESM5)                 │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │ Raw tick DataFrame
                       ↓
┌─────────────────────────────────────────────────────────────┐
│               continuous_adjustment.py                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  detect_rolls_from_databento()                       │   │
│  │  - Parses: SymbolMappingMsg events                   │   │
│  │  - Calculates: Price gaps at rolls                   │   │
│  │  - Returns: List[RollEvent]                          │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  panama_adjustment_backward()                        │   │
│  │  - Shifts: Historical prices by cumulative gaps      │   │
│  │  - Produces: Smooth continuous price series          │   │
│  │  - Saves: data_cache/adjusted_ticks/*.parquet        │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │ Adjusted tick DataFrame
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    tick_processor.py                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  resample_ticks_to_ohlcv()                           │   │
│  │  - Frequency: 1 second (configurable)                │   │
│  │  - Session-aware: No cross-session bars              │   │
│  │  - OHLCV aggregation: first/max/min/last/sum         │   │
│  │  - Saves: data_cache/resampled_1sec/*.parquet        │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │ OHLCV bars (1-second)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              validation/tick_resampling.py                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Checkpoint 1: Session-Aware Resampling              │   │
│  │  Checkpoint 2: OHLC Integrity                        │   │
│  │  Checkpoint 3: Indicator Values                      │   │
│  │  Checkpoint 4: Timestamp Continuity                  │   │
│  │  Checkpoint 5: No NaN Propagation                    │   │
│  └──────────────────────────────────────────────────────┘   │
│  - Generates: ValidationReport (JSON)                        │
│  - Fail-fast: Raises InvalidDataError on failure             │
└──────────────────────┬──────────────────────────────────────┘
                       │ Validated OHLCV bars
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    Data Consumers                            │
│  - VectorBT Backtester                                       │
│  - Strategy Optimization                                     │
│  - Live Scanner (Phase 3)                                    │
└──────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Step-by-Step Pipeline

#### Step 1: Raw Data Fetch

**Module:** `databento_provider.py`
**Function:** `fetch_tick_data_bulk()`

```python
# Input
symbols = ['ES', 'NQ']
start_date = '2020-01-01'
end_date = '2025-10-31'

# Process
for symbol in symbols:
    for chunk in 6-month periods:
        data = client.timeseries.get_range(
            dataset='GLBX.MDP3',
            symbols=f'{symbol}.v.0',  # Volume-based continuous
            schema='trades',          # Tick data
            start=chunk_start,
            end=chunk_end
        )
        # Save immediately (don't lose data!)
        cache.save_parquet(data, f'{symbol}_raw_{chunk_start}_{chunk_end}')

# Output
data_cache/raw_ticks/
  ├── ES_ticks_raw_2020-01-01_2020-06-30.parquet
  ├── ES_ticks_raw_2020-07-01_2020-12-31.parquet
  └── ...
```

**Data Format:**
```
Columns: ['ts_event', 'price', 'size', 'action', 'side', ...]
Index: DatetimeIndex (tick timestamps)
Size: ~245M rows for 5 years of ES
```

#### Step 2: Roll Detection

**Module:** `continuous_adjustment.py`
**Function:** `detect_rolls_from_databento()`

```python
# Input
mapping_events = get_symbol_mapping_events('ES', start_date, end_date)
tick_data = load_tick_data_from_cache('ES', adjusted=False)

# Process
rolls = []
for event in mapping_events:
    old_price = tick_data.loc[:event.date].iloc[-1]['price']
    new_price = tick_data.loc[event.date:].iloc[0]['price']
    gap = new_price - old_price

    rolls.append(RollEvent(
        date=event.date,
        old_contract=event.old_contract,
        new_contract=event.new_contract,
        gap=gap,
        symbol='ES'
    ))

# Output
data_cache/roll_metadata/
  └── ES_roll_events_2020-2025.json
```

**Roll Event Example:**
```json
{
  "date": "2024-03-14T13:30:00",
  "old_contract": "ESH4",
  "new_contract": "ESM4",
  "gap": 5.25,
  "symbol": "ES"
}
```

#### Step 3: Panama Adjustment

**Module:** `continuous_adjustment.py`
**Function:** `panama_adjustment_backward()`

```python
# Input
raw_ticks = load_tick_data_from_cache('ES', adjusted=False)
rolls = load_roll_metadata('ES')

# Process (backward adjustment)
adjusted = raw_ticks.copy()
for roll in reversed(sorted(rolls, key=lambda r: r.date)):
    # Shift all data BEFORE roll by gap amount
    mask = adjusted.index < roll.date
    adjusted.loc[mask, 'price'] -= roll.gap

# Output
data_cache/adjusted_ticks/
  └── ES_ticks_adjusted_2020-2025.parquet
```

**Before vs After:**
```
Before (raw):
  2024-03-14 13:29:59  ESH4  4800.00  ← Old contract
  2024-03-14 13:30:00  ESM4  4805.25  ← New contract (+5.25 gap)

After (adjusted):
  2024-03-14 13:29:59  ES    4800.00  ← Shifted backward by cumulative gaps
  2024-03-14 13:30:00  ES    4800.50  ← Smooth transition (gap removed)
```

#### Step 4: Resampling

**Module:** `tick_processor.py`
**Function:** `resample_ticks_to_ohlcv()`

```python
# Input
adjusted_ticks = load_tick_data_from_cache('ES', adjusted=True)

# Process (session-aware resampling)
bars = resample_with_session_awareness(
    adjusted_ticks,
    frequency='1s',
    session_gap_threshold=pd.Timedelta('5min')
)

ohlcv = bars.agg({
    'price': ['first', 'max', 'min', 'last'],
    'size': 'sum'
})
ohlcv.columns = ['open', 'high', 'low', 'close', 'volume']

# Output
data_cache/resampled_1sec/
  └── ES_1sec_adjusted_2020-2025.parquet
```

**OHLCV Format:**
```
                     open     high      low    close  volume
2025-10-31 17:00:00  4780.25  4781.00  4779.50  4780.75   12345
2025-10-31 17:00:01  4780.75  4781.25  4780.50  4781.00   23456
```

#### Step 5: Validation

**Module:** `validation/tick_resampling.py`
**Functions:** 5 checkpoint validators

```python
# Input
ohlcv = load_tick_data_from_cache('ES', adjusted=True)

# Process
report = ValidationReport()

# Checkpoint 1: Session alignment
validate_timestamp_alignment(ohlcv, frequency='1s')

# Checkpoint 2: OHLC integrity
validate_ohlc_integrity(ohlcv)

# Checkpoint 3: Indicator sanity
validate_indicator_values(ohlcv)

# Checkpoint 4: Continuity
validate_timestamp_continuity(ohlcv)

# Checkpoint 5: No NaNs
assert ohlcv.isna().sum().sum() == 0

# Output
if report.passed:
    print("✅ All checkpoints passed")
else:
    raise InvalidDataError("Validation failed")
```

---

## Module Responsibilities

### databento_provider.py

**Purpose:** Databento API interface

**Responsibilities:**
- Fetch tick data in chunks
- Retrieve SymbolMappingMsg events
- Estimate API costs
- Handle API errors and retries
- Save raw data to Parquet

**Key Functions:**
- `fetch_tick_data_bulk()` - Download historical ticks
- `get_symbol_mapping_events()` - Get roll dates
- `load_tick_data_from_cache()` - Load cached data
- `estimate_cost()` - Cost estimation

**Dependencies:**
- `databento` Python SDK
- `pandas` for DataFrames
- `cache.py` for Parquet I/O

### continuous_adjustment.py

**Purpose:** Continuous contract adjustment

**Responsibilities:**
- Detect roll events from SymbolMappingMsg
- Calculate price gaps at rolls
- Apply Panama back-adjustment
- Validate adjustment correctness
- Save roll metadata

**Key Functions:**
- `detect_rolls_from_databento()` - Parse roll events
- `panama_adjustment_backward()` - Adjust prices
- `validate_adjustment()` - Check results
- `save_roll_metadata()` - Persist metadata

**Dependencies:**
- `databento_provider.py` for SymbolMappingMsg
- `pandas` for time series ops
- `cache.py` for storage

### tick_processor.py

**Purpose:** Tick-to-bar resampling

**Responsibilities:**
- Resample ticks to OHLCV bars
- Session-aware aggregation (no cross-session bars)
- Integrate with validation checkpoints
- Orchestrate complete pipeline
- Progress tracking and logging

**Key Functions:**
- `resample_ticks_to_ohlcv()` - Tick aggregation
- `process_symbol_bulk()` - Complete pipeline orchestrator
- `run_all_validation_checkpoints()` - Validation wrapper

**Dependencies:**
- `databento_provider.py` for data
- `continuous_adjustment.py` for adjustment
- `validation/tick_resampling.py` for checks
- `cache.py` for storage

### cache.py

**Purpose:** Parquet storage abstraction

**Responsibilities:**
- Save DataFrames to Parquet (compressed)
- Load with date/column filters (fast)
- Metadata management
- Cache invalidation
- File naming conventions

**Key Functions:**
- `save_parquet()` - Write compressed Parquet
- `load_parquet()` - Read with filters
- `get_parquet_metadata()` - File stats

**Dependencies:**
- `pandas` for Parquet I/O
- `pyarrow` for compression

### validation/tick_resampling.py

**Purpose:** Data quality validation

**Responsibilities:**
- 5 checkpoint protocol enforcement
- Session detection and verification
- OHLC integrity checks
- Indicator sanity validation
- Generate validation reports

**Key Functions:**
- `resample_with_session_awareness()` - Session-aware resampling
- `validate_ohlc_integrity()` - Checkpoint 2
- `validate_timestamp_alignment()` - Checkpoint 1
- `validate_indicator_values()` - Checkpoint 3
- `ValidationReport` - Report dataclass

**Dependencies:**
- `pandas` for data checks
- `numpy` for calculations
- `indicators/` for test indicators

---

## Continuous Contract System

### Why Continuous Contracts?

Futures contracts have expiration dates. For backtesting, we need a single continuous price series spanning years.

**Problem:**
```
ESH5 expires March 2025 → Gap to ESM5 (June 2025)
ESM5 expires June 2025  → Gap to ESU5 (September 2025)
```

**Solution:** Continuous contracts with back-adjustment

### Volume-Based Roll (`.v.0`)

Databento uses `.v.0` symbology for volume-based continuous contracts:

**Roll Trigger:** Switch to next contract when its volume exceeds current contract

```
ESH5 (March 2025 contract)
  ↓ Volume crossover (Feb 15, 2025)
ESM5 (June 2025 contract)
```

**Advantages:**
- Rolls before expiration (avoids delivery issues)
- Follows market liquidity
- Automated by Databento

### Roll Detection

Databento sends `SymbolMappingMsg` when rolls occur:

```json
{
  "ts_event": "2025-02-15T13:30:00",
  "stype_in_symbol": "ES.v.0",       // Continuous symbol
  "stype_out_symbol": "ESH5",        // Old contract
  "new_stype_out_symbol": "ESM5",    // New contract
  "start_ts": "2025-02-15T13:30:00",
  "end_ts": null
}
```

We parse these events to detect:
- Roll date
- Old/new contract pair
- Price gap to adjust

---

## Panama Adjustment Algorithm

### Backward Adjustment (Standard)

**Goal:** Remove price gaps at roll dates by shifting historical data

**Algorithm:**
```
1. Collect all roll events (sorted by date)
2. For each roll (newest to oldest):
     gap = new_contract_price - old_contract_price
     For all data BEFORE roll:
         price -= gap
3. Result: Smooth continuous series
```

**Example:**

```
Raw Data (5 years, 3 rolls):

2023-03-15: ESM3 → ESU3, gap = +8.50
2023-09-15: ESU3 → ESZ3, gap = +3.25
2024-03-15: ESZ3 → ESH4, gap = +5.75

Cumulative gaps for old data:
  Before 2024-03-15: -5.75
  Before 2023-09-15: -5.75 - 3.25 = -9.00
  Before 2023-03-15: -9.00 - 8.50 = -17.50

Adjusted:
  2020-01-01 price: 3200.00 - 17.50 = 3182.50
  2023-09-16 price: 4500.00 - 5.75  = 4494.25
  2024-03-16 price: 4780.00 - 0.00  = 4780.00 (recent data unchanged)
```

**Characteristics:**
- Recent prices match current market
- Old prices shifted downward
- Negative prices possible (expected)
- Smooth transitions at rolls

### Forward Adjustment (Alternative)

**Goal:** Keep old prices intact, shift recent data

**Less common** - used when you want historical prices to match original values.

---

## Caching Strategy

### Three-Tier Cache

```
1. Raw Ticks (largest, rarely accessed)
   data_cache/raw_ticks/
   ├── ES_ticks_raw_*.parquet
   └── ~50 GB per symbol (5 years)

2. Adjusted Ticks (medium, occasional access)
   data_cache/adjusted_ticks/
   ├── ES_ticks_adjusted_*.parquet
   └── ~48 GB per symbol (compressed)

3. Resampled Bars (smallest, frequent access)
   data_cache/resampled_1sec/
   ├── ES_1sec_adjusted_*.parquet
   └── ~6 GB per symbol (highly compressed)
```

### Parquet Benefits

- **Compression:** 5-10x smaller than CSV/pickle
- **Speed:** Columnar format, 100x faster reads
- **Filtering:** Load specific date ranges without full scan
- **Schema:** Preserves types (no CSV parsing)

### Cache Invalidation

Cache is invalidated when:
- New data downloaded (extends date range)
- Adjustment method changes
- Resampling frequency changes

**Never invalidate** for:
- Code updates (data unchanged)
- New indicators (calculate on-the-fly)

---

## Validation Pipeline

### 5 Checkpoint Protocol

See [AGENT_BACKTEST_PROTOCOL.md](AGENT_BACKTEST_PROTOCOL.md) for complete details.

**Checkpoint 1: Session-Aware Resampling**
- Bars align to session start times
- No cross-session bars
- Gaps only at session breaks

**Checkpoint 2: OHLC Integrity**
- High >= Open, Close, Low
- Low <= Open, Close, High
- No violations

**Checkpoint 3: Indicator Values**
- Indicators within expected ranges
- No infinite/NaN values
- Visual verification possible

**Checkpoint 4: Timestamp Continuity**
- No missing bars within sessions
- Frequency maintained
- Gaps align with known breaks

**Checkpoint 5: No NaN Propagation**
- Zero NaN values in final data
- All calculations complete
- Data ready for backtesting

### Validation Reports

Saved to `data_cache/validation/`:

```json
{
  "symbol": "ES",
  "frequency": "1s",
  "date_range": ["2020-01-01", "2025-10-31"],
  "checkpoints": {
    "session_awareness": {"passed": true, "details": "..."},
    "ohlc_integrity": {"passed": true, "violations": 0},
    "indicator_values": {"passed": true, "ranges": "..."},
    "timestamp_continuity": {"passed": true, "gaps": 0},
    "nan_propagation": {"passed": true, "nan_count": 0}
  },
  "overall": "PASSED",
  "timestamp": "2025-10-31T12:00:00"
}
```

---

## Error Handling

### Exception Hierarchy

```
DataException (base)
├── DataFetchError
│   ├── APIKeyError
│   ├── RateLimitError
│   └── NetworkError
├── InvalidDataError
│   ├── ValidationError
│   ├── IntegrityError
│   └── MissingDataError
└── CacheError
    ├── CacheCorruptedError
    └── CacheNotFoundError
```

### Error Handling Strategy

**Fail-Fast:** Never propagate invalid data

```python
try:
    data = fetch_tick_data_bulk(symbols, start_date, end_date)
except DataFetchError as e:
    logger.error(f"Download failed: {e}")
    # Clean up partial downloads
    cleanup_partial_cache()
    raise  # Don't continue with invalid data

try:
    adjusted = panama_adjustment_backward(data, rolls)
    report = validate_adjustment(data, adjusted, rolls)
    if not report['all_passed']:
        raise InvalidDataError(f"Adjustment failed: {report}")
except InvalidDataError as e:
    logger.error(f"Data quality issue: {e}")
    # Don't save invalid data
    raise
```

**Retry Logic:** Not implemented initially (fail-fast approach)

---

## Performance Considerations

### Throughput

**Download:**
- Tick data: ~6M ticks/minute
- 5 years ES: ~245M ticks = 40 minutes
- Bottleneck: Network (Databento API)

**Adjustment:**
- 245M rows: ~3 minutes
- Bottleneck: Memory bandwidth

**Resampling:**
- 245M ticks → 8M bars: ~8 minutes
- Bottleneck: CPU (groupby operations)

**Validation:**
- 8M bars: ~2 minutes
- Bottleneck: Indicator calculations

**Total:** ~55 minutes for 5 years of ES data (one-time)

### Memory Usage

**Peak Memory:**
- Raw ticks in memory: ~18 GB (245M rows × 8 columns × 8 bytes)
- Adjusted ticks: ~18 GB (copy)
- Resampled bars: ~600 MB (8M rows)

**Chunked Processing:**
- Download in 6-month chunks: ~3 GB per chunk
- Save immediately (don't accumulate)
- Total memory: ~6 GB peak (manageable)

### Storage

**Per Symbol (5 years):**
- Raw ticks: ~50 GB (uncompressed)
- Adjusted ticks: ~48 GB
- Resampled 1s bars: ~6 GB (Parquet compressed)

**Total for 5 symbols (ES, NQ, GC, ZB, ZC):**
- ~250 GB raw + adjusted
- ~30 GB resampled (this is what backtests use)

**Recommendation:** Keep only resampled bars for production (~30 GB)

---

## Summary

### Key Takeaways

1. **Modular Design** - Each module has clear, single responsibility
2. **Cache-First** - Download once, reuse forever
3. **Validation-Driven** - 5 checkpoints ensure data quality
4. **Fail-Fast** - Invalid data never enters system
5. **Parquet-Native** - Efficient storage, fast access

### Next Steps

- **[DATABENTO_USAGE.md](DATABENTO_USAGE.md)** - Learn common workflows
- **[CONTINUOUS_CONTRACTS_EXPLAINED.md](CONTINUOUS_CONTRACTS_EXPLAINED.md)** - Deep dive into futures contracts
- **[notebooks/databento_example.ipynb](../../notebooks/databento_example.ipynb)** - Hands-on tutorial

---

**Last Updated:** October 31, 2025
**Vector Bot Version:** 3.0+
