#!/bin/bash
#
# check_databento_safety.sh
# ==========================
# Checks for unsafe direct calls to vbt.BentoData.download()
#
# Usage:
#   ./scripts/check_databento_safety.sh
#   ./scripts/check_databento_safety.sh examples/my_script.py
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Checking for unsafe Databento API calls..."
echo ""

# Directories to check (or use command-line args)
if [ $# -eq 0 ]; then
    PATHS=(
        "data/"
        "strategies/"
        "examples/"
        "scripts/"
        "scanner/"
    )
else
    PATHS=("$@")
fi

# Collect all Python files
ALL_FILES=()
for path in "${PATHS[@]}"; do
    if [ ! -e "$path" ]; then
        echo "⚠️  Path not found: $path"
        continue
    fi

    if [ -f "$path" ]; then
        # Single file
        ALL_FILES+=("$path")
    else
        # Directory - find all Python files
        while IFS= read -r -d '' file; do
            ALL_FILES+=("$file")
        done < <(find "$path" -name "*.py" -type f -print0 2>/dev/null)
    fi
done

# Check each file
VIOLATIONS=0

for file in "${ALL_FILES[@]}"; do
    # Check if file has vbt.BentoData.download() call
    if grep -q "vbt\.BentoData\.download(" "$file" 2>/dev/null; then
        # Check if file imports safe_download
        if ! grep -q "from data.databento_safe_download import" "$file"; then
            # VIOLATION
            echo ""
            echo -e "${RED}❌ VIOLATION:${NC} $file"
            echo "   Direct vbt.BentoData.download() without safe_download wrapper"
            echo ""
            echo "   Lines:"
            grep -n "vbt\.BentoData\.download(" "$file" | head -3
            echo ""
            VIOLATIONS=$((VIOLATIONS + 1))
        fi
    fi
done

echo "════════════════════════════════════════════════════════════════"

if [ $VIOLATIONS -eq 0 ]; then
    echo -e "${GREEN}✅ PASS:${NC} All Databento API calls use safe_download wrapper"
    echo "════════════════════════════════════════════════════════════════"
    exit 0
else
    echo -e "${RED}❌ FAIL:${NC} Found $VIOLATIONS file(s) with unsafe Databento API calls"
    echo ""
    echo "Fix:"
    echo "  1. Replace vbt.BentoData.download() with safe_download()"
    echo "  2. Add: from data.databento_safe_download import safe_download"
    echo ""
    echo "See: claude.md (Databento Integration → Safe Download Wrapper)"
    echo "════════════════════════════════════════════════════════════════"
    exit 1
fi
