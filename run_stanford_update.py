#!/usr/bin/env python3
"""
Stanford scraper to update 2025-2026 academic year data
"""

import os
import sys
sys.path.insert(0, 'stanford')

# Set API key
os.environ['SCRAPER_API_KEY'] = 'a88fb9ea05164d97e8281f635f60f618'

from stanford_enrollment_scraper import StanfordScraperAPI
import pandas as pd

print("Starting Stanford 2025-2026 academic year update...")
print("⚠️  This will scrape the entire 2025-2026 academic year")
print("    This may take 30-60 minutes due to rate limiting\n")

scraper = StanfordScraperAPI()

if not scraper.api_key:
    print("❌ API key not set")
    sys.exit(1)

print(f"✅ API key configured")
print(f"📡 Using ScraperAPI service\n")

# The scraper will scrape all available academic years
# We need to run it and then filter for 2025-2026
print("🔍 Starting scraping process...")
print("   This will take a while - scraper has built-in rate limiting\n")

# Run the scraper's main method
try:
    scraper.scrape_all()
    scraper.save_results()
    print("\n✅ Stanford scraping complete!")
except Exception as e:
    print(f"\n❌ Error during scraping: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
