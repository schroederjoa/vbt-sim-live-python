   1 +  # Databento Integration - Salvage Guide
         2 +
         3 +  **Purpose:** Extract the critical cost protection pattern from vector_bot for reuse in new trading
           + system.
         4 +
         5 +  **TL;DR:** The safe download wrapper that enforces `get_cost()` checks is the most valuable piece.
           + Everything else is standard Databento API usage.
         6 +
         7 +  ---
         8 +
         9 +  ## The One Critical Requirement
        10 +
        11 +  ### ALWAYS Check Cost Before Downloading
        12 +
        13 +  ```python
        14 +  # ❌ NEVER DO THIS
        15 +  data = vbt.BentoData.download(...)  # Could cost $100+ instantly!
        16 +
        17 +  # ✅ ALWAYS DO THIS
        18 +  cost = vbt.BentoData.get_cost(...)  # Check first
        19 +  if cost > 0:
        20 +      raise Error("Not covered by plan!")
        21 +  data = vbt.BentoData.download(...)  # Only if cost = $0
        22 +  ```
        23 +
        24 +  **Why This Matters:**
        25 +  - Databento charges per query (pay-per-use)
        26 +  - Standard Plan ($179/month) has "unlimited" CME futures, but you must verify
        27 +  - `get_cost()` returns `0.0` if data is included in plan
        28 +  - Forgetting this check can cost $100+ in one accidental query
        29 +
        30 +  ---
        31 +
        32 +  ## The Safe Download Wrapper
        33 +
        34 +  ### File Location
        35 +  `data/databento_safe_download.py` (239 lines)
        36 +
        37 +  ### Core Pattern
        38 +
        39 +  ```python
        40 +  def safe_download(dataset, symbols, schema, start, end, max_cost=10.0):
        41 +      """Wrapper that enforces cost check."""
        42 +
        43 +      # 1. Check cost FIRST
        44 +      cost = vbt.BentoData.get_cost(
        45 +          dataset=dataset,
        46 +          symbols=symbols,
        47 +          schema=schema,
        48 +          start=start,
        49 +          end=end,
        50 +      )
        51 +
        52 +      # 2. Abort if cost > limit
        53 +      if cost > max_cost:
        54 +          raise ValueError(f"Cost ${cost} exceeds ${max_cost} limit")
        55 +
        56 +      # 3. Prompt user if any cost
        57 +      if cost > 0:
        58 +          response = input(f"Proceed with ${cost} charge? (yes/no): ")
        59 +          if response != 'yes':
        60 +              return None
        61 +
        62 +      # 4. Only download if approved
        63 +      return vbt.BentoData.download(dataset, symbols, schema, start, end)
        64 +  ```
        65 +
        66 +  ### Batch Version
        67 +
        68 +  ```python
        69 +  def safe_download_batch(dataset, symbols, schema, start, end, max_cost=10.0):
        70 +      """Check TOTAL cost across all symbols before downloading any."""
        71 +
        72 +      total_cost = sum(
        73 +          vbt.BentoData.get_cost(dataset, sym, schema, start, end)
        74 +          for sym in symbols
        75 +      )
        76 +
        77 +      if total_cost > max_cost:
        78 +          raise ValueError(f"Total ${total_cost} exceeds ${max_cost}")
        79 +
        80 +      # Download all if approved
        81 +      return {sym: vbt.BentoData.download(...) for sym in symbols}
        82 +  ```
        83 +
        84 +  ---
        85 +
        86 +  ## Enforcement: Safety Check Script
        87 +
        88 +  ### File Location
        89 +  `scripts/check_databento_safety.sh` (93 lines)
        90 +
        91 +  ### What It Does
        92 +  Scans codebase for unsafe direct calls to `vbt.BentoData.download()`:
        93 +
        94 +  ```bash
        95 +  #!/bin/bash
        96 +  # Find files calling vbt.BentoData.download() WITHOUT safe_download wrapper
        97 +
        98 +  for file in $(find . -name "*.py"); do
        99 +      if grep -q "vbt\.BentoData\.download(" "$file"; then
       100 +          if ! grep -q "from data.databento_safe_download import" "$file"; then
       101 +              echo "❌ VIOLATION: $file"
       102 +              grep -n "vbt\.BentoData\.download(" "$file"
       103 +          fi
       104 +      fi
       105 +  done
       106 +  ```
       107 +
       108 +  **Run Before Every Commit:**
       109 +  ```bash
       110 +  ./scripts/check_databento_safety.sh
       111 +  ```
       112 +
       113 +  ---
       114 +
       115 +  ## Standard Databento Configuration
       116 +
       117 +  ```python
       118 +  # CME futures via Databento
       119 +  DATABENTO_CONFIG = {
       120 +      "dataset": "GLBX.MDP3",      # CME Globex
       121 +      "stype_in": "continuous",    # Continuous contracts
       122 +      "schema": "ohlcv-1M",        # 1-minute bars
       123 +  }
       124 +
       125 +  # Continuous contract symbols (volume-based rolls)
       126 +  SYMBOLS = {
       127 +      "ES": "ES.v.0",  # E-mini S&P 500
       128 +      "NQ": "NQ.v.0",  # E-mini NASDAQ
       129 +      "GC": "GC.v.0",  # Gold
       130 +  }
       131 +  ```
       132 +
       133 +  ---
       134 +
       135 +  ## Setup Requirements
       136 +
       137 +  **API Key:**
       138 +  - Get API key from databento.com (Account → API Keys)
       139 +  - Store in `.env` file: `DATABENTO_API_KEY=db-YOUR_KEY_HERE`
       140 +  - Never commit `.env` to git (add to `.gitignore`)
       141 +
       142 +  **Session-Aware Resampling:**
       143 +  - ES futures have daily gaps (5pm-6pm ET maintenance window)
       144 +  - If resampling from tick/1s data to higher frequencies (e.g., 1s → 27min), use session-aware resampling
       145 +  - Prevents bars from spanning session breaks (e.g., 21:55 → 22:20 bar crosses the gap)
       146 +  - Only needed for custom frequencies (Databento provides pre-resampled bars: `ohlcv-1s`, `ohlcv-1m`)
       147 +  - Implementation available in old repo: `validation/tick_resampling.py` (function: `resample_with_session_awareness`)
       148 +
       149 +  ---
       150 +
       151 +  ## Usage Examples
       136 +
       137 +
       150 +
       151 +
       165 +  ---
       166 +
       167 +  ## Additional Files Worth Reviewing
       168 +
       177
       178 + **Documentation:**
       180 +  - `docs/guides/DATABENTO_ARCHITECTURE.md` - System architecture
       181 +  - Needs to be added to `claude.md`
       182 +
       1
       186 +
       187 +  ---
       188 +
       189 +  ## Key Takeaways for New Repo
       190 +
       191 +  1. **Copy these 2 files:**
       192 +     - `data/databento_safe_download.py`
       193 +     - `scripts/check_databento_safety.sh`
       194 +
       195 +  2. **Enforce the rule:**
       196 +     - Run safety check script in CI/CD
       197 +     - Block commits with unsafe calls
       202 +
       203 +  4. **That's it.**
       204 +     - Everything else is standard Databento usage
       205 +     - No need to overcomplicate
       206 +
       207 +  ---
       208 +
       209 +  **Date:** 2025-11-10
       210 +  **Status:** Ready for new repository
       211 +  **Files to Copy:** 2 (safe_download.py + check_safety.sh)
