# Fall 2025-26 Data Update Status

**Date:** November 18, 2025
**Attempted in:** Containerized environment (Claude Code)

## Current Data Status

| University | Term | Last Updated | Courses | Age | Status |
|------------|------|--------------|---------|-----|--------|
| **Princeton** | Fall 2025-26 | Aug 1, 2025 | 1,589 | 3.5 months | 🟡 Needs refresh |
| **Stanford** | Fall 2025 (2025-26) | N/A | 0 | N/A | ❌ **MISSING** |
| **Harvard** | Fall 2025-26 | **Oct 31, 2025** | **3,055** | **18 days** | ✅ **UPDATED** |

## Environment Limitations Encountered

### Princeton Scraper
- **Issue:** Chrome/Chromium crashes in containerized environment
- **Error:** `tab crashed` / `session not created`
- **Cause:** Headless Chrome has memory/permission issues in Docker/containers
- **Status:** ❌ Failed

### Stanford Scraper
- **Issue:** Finding 0 courses for all departments
- **Possible Causes:**
  1. Stanford website structure changed
  2. ScraperAPI having issues with Stanford's site
  3. Year code 2025-2026 not yet available on Stanford's website
- **Year Coverage:** Scraper only configured for 2021-2025, missing 2025-2026
- **Status:** ⚠️  Needs investigation

### Harvard Data
- **Issue:** No automated scraper (manual CSV download required)
- **Source:** https://registrar.fas.harvard.edu/links/archive/enrollment-reports
- **Status:** ✅ **UPDATED - Oct 31, 2025**
- **Previous data:** 2,177 courses (April 17, 2025)
- **New data:** 3,055 courses (October 31, 2025)
- **Improvement:** +878 courses (+40.3%)

## Scripts Created

### 1. `update_fall_2025_26.py`
General update script with instructions for all three universities.

### 2. `run_princeton_update.py`
Modified Princeton scraper with headless Chrome configuration.

### 3. `run_stanford_update.py`
Stanford scraper with API key integration (attempts all years 2021-2025).

### 4. `run_stanford_2025_only.py`
Targeted Stanford scraper for 2025-2026 only.

## Recommendations for Local Setup

### Option 1: Run in Local Environment (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd course_enrollment

# Install dependencies
pip install -r requirements.txt

# For Princeton (requires Chrome)
cd princeton
python3 princeton_enrollment_scraper.py

# For Stanford (requires API key)
export SCRAPER_API_KEY='a88fb9ea05164d97e8281f635f60f618'
cd stanford
python3 stanford_enrollment_scraper.py

# For Harvard
# Download latest CSV from https://registrar.fas.harvard.edu/links/archive/enrollment-reports
# Save as harvard/harvard_enrollment_2025_2026_fall.csv
```

### Option 2: Fix Stanford Scraper

The Stanford scraper needs investigation:

1. **Check if 2025-2026 exists** on Stanford's website
2. **Verify year code format** (is it `20252026` or different?)
3. **Test URL directly**: https://explorecourses.stanford.edu/search?academicYear=20252026
4. **Update scraper** if Stanford changed their HTML structure

### Option 3: Manual Data Collection

If scrapers continue to fail:

1. **Princeton**: Visit https://registrar.princeton.edu/course-offerings
   - Select Fall 2025-26
   - Export/scrape manually

2. **Stanford**: Visit https://explorecourses.stanford.edu
   - Browse 2025-2026 courses
   - Consider requesting data dump from registrar

3. **Harvard**: Already manual - just download latest CSV

## Files to Commit

- ✅ `update_fall_2025_26.py` - Main update script
- ✅ `run_princeton_update.py` - Princeton specific script
- ✅ `run_stanford_update.py` - Stanford all-years script
- ✅ `run_stanford_2025_only.py` - Stanford 2025-26 only
- ✅ `UPDATE_STATUS.md` - This file

## Next Steps

1. Run scrapers in local environment with Chrome and API access
2. Investigate Stanford 0-course issue
3. Update CSV files with fresh data
4. Commit updated CSVs to repository

## API Key

**ScraperAPI Key:** `a88fb9ea05164d97e8281f635f60f618`
**Account:** Should be set as environment variable
**Usage:** Use for Stanford scraper only

⚠️  **Security Note:** This API key is exposed in scripts. Consider rotating it after use or storing in environment variables only.
