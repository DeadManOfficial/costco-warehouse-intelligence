# KAGGLE DATASET DOWNLOAD GUIDE

**Mission:** Download free Kaggle datasets for Costco warehouse database
**Agent:** AGENT 2 - Kaggle Dataset Integration Specialist
**Date:** 2026-01-10

---

## TARGET DATASETS

### 1. Mikestokholm Dataset (Feb 2020)
- **URL:** https://www.kaggle.com/datasets/mikestokholm/costco-warehouse-information
- **Records:** 783 warehouses
- **Strengths:** Has warehouse numbers, complete addresses
- **Weaknesses:** 5 years old (some stores may be closed)
- **Priority:** HIGH (Primary source for warehouse numbers)

### 2. Polartech Dataset (May 2022)
- **URL:** https://www.kaggle.com/datasets/polartech/complete-store-locations-of-costco
- **Records:** US, UK, Canada locations
- **Strengths:** More recent data, international coverage
- **Weaknesses:** Missing warehouse numbers
- **Priority:** MEDIUM (Update layer for recent addresses)

---

## DOWNLOAD METHODS

### Method 1: Kaggle API (Automated - Recommended)

**Prerequisites:**
1. Kaggle account (free signup at kaggle.com)
2. Kaggle API credentials

**Setup Steps:**

1. **Install Kaggle API** (Already done)
   ```bash
   pip install kaggle
   ```

2. **Get API Credentials**
   - Go to: https://www.kaggle.com/settings/account
   - Scroll to "API" section
   - Click "Create New API Token"
   - This downloads `kaggle.json` to your Downloads folder

3. **Install Credentials**
   - Windows: Move to `C:\Users\Administrator\.kaggle\kaggle.json`
   - Linux/Mac: Move to `~/.kaggle/kaggle.json`
   - Set permissions (Linux/Mac only): `chmod 600 ~/.kaggle/kaggle.json`

4. **Download Datasets**
   ```bash
   python Scripts/merge_kaggle_datasets.py --download
   ```

**Expected Output:**
```
[DOWNLOAD] Attempting to download datasets via Kaggle API...
[DOWNLOAD] Downloading mikestokholm/costco-warehouse-information...
[SUCCESS] Downloaded mikestokholm/costco-warehouse-information
[DOWNLOAD] Downloading polartech/complete-store-locations-of-costco...
[SUCCESS] Downloaded polartech/complete-store-locations-of-costco
```

---

### Method 2: Manual Download (Fallback)

If Kaggle API fails or credentials are not available:

**Step 1: Download Mikestokholm Dataset**
1. Go to: https://www.kaggle.com/datasets/mikestokholm/costco-warehouse-information
2. Click "Download" button (top right)
3. Save ZIP file to: `D:\Data\kaggle_datasets\mikestokholm\`
4. Extract ZIP contents in that folder

**Step 2: Download Polartech Dataset**
1. Go to: https://www.kaggle.com/datasets/polartech/complete-store-locations-of-costco
2. Click "Download" button (top right)
3. Save ZIP file to: `D:\Data\kaggle_datasets\polartech\`
4. Extract ZIP contents in that folder

**Step 3: Verify Files**
```bash
ls D:/Data/kaggle_datasets/mikestokholm/*.csv
ls D:/Data/kaggle_datasets/polartech/*.csv
```

**Step 4: Run Merger**
```bash
python Scripts/merge_kaggle_datasets.py --merge
```

---

## EXPECTED FILE STRUCTURE

After download, you should have:

```
D:/Data/
├── kaggle_datasets/
│   ├── mikestokholm/
│   │   └── costco_warehouses.csv (or similar)
│   └── polartech/
│       └── costco_locations.csv (or similar)
└── costco_warehouses.json (existing 60 warehouses)
```

---

## MERGE STRATEGY

The merger script will:

1. **Load Mikestokholm** (primary source - has warehouse numbers)
2. **Load Polartech** (update layer - more recent addresses)
3. **Load Existing 60 Warehouses** (validation layer)
4. **Fuzzy Match** warehouses by address similarity
5. **Merge Intelligently:**
   - Preserve warehouse numbers from Mikestokholm
   - Update addresses from Polartech if match found
   - Validate against existing 60 warehouses
   - Flag conflicts for manual review
6. **Generate Output:**
   - `costco_warehouses_kaggle.json` (merged database)
   - `kaggle_merge_conflicts.json` (conflicts to review)
   - `agent_reports/kaggle_integration.md` (comprehensive report)

---

## MATCHING ALGORITHM

**Address Normalization:**
- Convert to lowercase
- Standardize abbreviations (Street → St, Avenue → Ave, etc.)
- Remove punctuation
- Normalize spacing

**Fuzzy Matching:**
- Uses Python's `difflib.SequenceMatcher`
- Calculates similarity ratio (0-1)
- Threshold: 0.8 (80% match required)

**Weighted Scoring:**
- Address similarity: 70%
- City similarity: 30%
- Combined score determines match quality

**Example:**
```
Warehouse A: "2301 Showers Drive, Mountain View, CA"
Warehouse B: "2301 showers dr, mountain view, california"

Normalized A: "2301 showers dr mountain view ca"
Normalized B: "2301 showers dr mountain view california"

Address Similarity: 0.95
City Similarity: 1.0
Combined Score: (0.95 * 0.7) + (1.0 * 0.3) = 0.965 = 96.5% match
```

---

## CONFLICT RESOLUTION

Conflicts occur when:
- Same warehouse number has different addresses in multiple sources
- Address similarity < 80% between Kaggle and existing data

**Conflict Output Format:**
```json
{
  "warehouse_number": "428",
  "kaggle_address": "2207 West Commonwealth Avenue",
  "existing_address": "2207 W Commonwealth Ave",
  "similarity": 0.875
}
```

**Resolution Actions:**
1. Review conflicts in `kaggle_merge_conflicts.json`
2. For similarity > 75%: Likely same warehouse, different formatting
3. For similarity < 75%: May be relocation or data error
4. Manually verify on Costco.com warehouse locator
5. Update merged database accordingly

---

## SUCCESS METRICS

**Target:** 400-500 warehouses with validated data

**Quality Indicators:**
- Warehouse numbers: 100% (Mikestokholm has all)
- Complete addresses: >95%
- ZIP codes: >90%
- Validated against existing: All 60 checked
- Match confidence: >85% average

**Expected Results:**
- Mikestokholm: 783 warehouses (some may be closed)
- After validation: 400-500 active warehouses
- With warehouse numbers: 100%
- Geographic coverage: All US states + international

---

## TROUBLESHOOTING

### "Kaggle credentials not found"
**Solution:** Follow Method 2 (Manual Download) or setup API credentials

### "CSV file not found"
**Solution:** Check file extraction, CSV may have different name. Script auto-detects.

### "No matches found"
**Solution:** Column names may differ. Script uses intelligent column detection.

### "Too many conflicts"
**Solution:** Normal if datasets are from different years. Review conflicts manually.

---

## NEXT STEPS AFTER MERGE

1. **Review Report:** Check `Data/agent_reports/kaggle_integration.md`
2. **Validate Conflicts:** Review `kaggle_merge_conflicts.json`
3. **Cross-Reference:** Compare with Costco.com official locator
4. **Enrich Data:** Add coordinates (lat/lon) for geocoding
5. **Update Production:** Integrate with `warehouse_runner_PRODUCTION.py`
6. **Enumerate Missing:** Use enumeration (100-999) for missing warehouses
7. **Build Master DB:** Combine with other sources (OSM, official scraping)

---

## AGENT COORDINATION

**This Agent (AGENT 2) Outputs:**
- `costco_warehouses_kaggle.json` - Merged Kaggle data

**Inputs for Other Agents:**
- **AGENT 1:** Costco.com official scraper results
- **AGENT 3:** Enumeration results (warehouse numbers 100-999)
- **AGENT 4:** Master database builder

**Handoff to AGENT 4:**
- Once Kaggle merge complete, AGENT 4 combines all sources
- Target: 639 warehouses with 100% coverage

---

## COMMAND QUICK REFERENCE

```bash
# Install Kaggle API
pip install kaggle

# Check credentials
ls C:/Users/Administrator/.kaggle/kaggle.json

# Download datasets (automated)
python Scripts/merge_kaggle_datasets.py --download

# Merge datasets (after download)
python Scripts/merge_kaggle_datasets.py --merge

# Check output
cat Data/costco_warehouses_kaggle.json
cat Data/agent_reports/kaggle_integration.md

# Review conflicts
cat Data/kaggle_merge_conflicts.json
```

---

## FREE SOLUTIONS PHILOSOPHY

**BUILD vs BUY:**
- Kaggle datasets: FREE
- Merger script: FREE (we built it)
- Total cost: $0
- Total time: 1-2 hours
- Ownership: 100% (we control updates)

**Alternative (Rejected):**
- ScrapeHero dataset: $80
- Single snapshot
- No customization
- Vendor dependency

**DeadMan's Directive:** "The creation and utilization of something free is way more practical"

---

**Document:** KAGGLE_DOWNLOAD_GUIDE.md
**Version:** 1.0
**Date:** 2026-01-10
**Agent:** AGENT 2 - Kaggle Dataset Integration Specialist
**Status:** Ready for execution
