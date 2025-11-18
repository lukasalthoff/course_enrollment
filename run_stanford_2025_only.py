#!/usr/bin/env python3
"""
Stanford scraper - 2025-2026 academic year ONLY
"""

import os
import sys
sys.path.insert(0, 'stanford')

# Set API key
os.environ['SCRAPER_API_KEY'] = 'a88fb9ea05164d97e8281f635f60f618'

# Patch the scraper to only get 2025-2026
import importlib.util
spec = importlib.util.spec_from_file_location("stanford_scraper", "stanford/stanford_enrollment_scraper.py")
module = importlib.util.module_from_spec(spec)

# Read and modify the source
source = open("stanford/stanford_enrollment_scraper.py").read()

# Replace the years list to only include 2025-2026
modified_source = source.replace(
    """return [
                {'code': '20212022', 'name': '2021-2022'},
                {'code': '20222023', 'name': '2022-2023'},
                {'code': '20232024', 'name': '2023-2024'},
                {'code': '20242025', 'name': '2024-2025'},
            ]""",
    """return [
                {'code': '20252026', 'name': '2025-2026'},
            ]"""
)

# Also update the fallback at the end
modified_source = modified_source.replace(
    "return years or [{'code': '20242025', 'name': '2024-2025'}]",
    "return years or [{'code': '20252026', 'name': '2025-2026'}]"
)

print("🎓 Stanford 2025-2026 Scraper")
print("="*60)
print("✅ API key configured")
print("🎯 Target: 2025-2026 academic year ONLY")
print("📡 Using ScraperAPI service\n")

# Execute the modified code
exec_globals = {}
exec(modified_source, exec_globals)

# Run the scraper
StanfordScraperAPI = exec_globals['StanfordScraperAPI']
scraper = StanfordScraperAPI()

print("🔍 Starting scraping for 2025-2026...")
print("   This will take 20-40 minutes due to rate limiting\n")

try:
    scraper.scrape_all()
    scraper.save_results()
    print("\n✅ Stanford 2025-2026 scraping complete!")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
