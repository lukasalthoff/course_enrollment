#!/usr/bin/env python3
"""
Modified Princeton scraper for containerized environments
"""

import sys
import os
sys.path.insert(0, 'princeton')

# Modify the scraper before importing
import importlib.util
spec = importlib.util.spec_from_file_location("scraper", "princeton/princeton_enrollment_scraper.py")
scraper_module = importlib.util.module_from_spec(spec)

# Patch the setup_browser method
original_code = open("princeton/princeton_enrollment_scraper.py").read()

# Execute with modifications
exec_globals = {}
modified_code = original_code.replace(
    "options.add_argument('--no-sandbox')",
    """options.add_argument('--no-sandbox')
            options.add_argument('--headless=new')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-software-rasterizer')
            options.add_argument('--disable-extensions')
            options.add_argument('--single-process')
            options.add_argument('--disable-setuid-sandbox')"""
)

exec(modified_code, exec_globals)

# Now run the scraper
import pandas as pd
import time

print("Starting Princeton Fall 2025-26 update (headless mode)...")

PrincetonFixedScraper = exec_globals['PrincetonFixedScraper']
scraper = PrincetonFixedScraper()

if not scraper.setup_browser():
    print('❌ Failed to setup browser')
    sys.exit(1)

# Get available terms
available_terms = scraper.get_available_terms()
if not available_terms:
    print('❌ Could not get terms')
    scraper.driver.quit()
    sys.exit(1)

print(f'✅ Found {len(available_terms)} terms')

# Find Fall 2025-26
fall_2025_26 = None
for term in available_terms:
    if '25-26 Fall' in term['text'] or term['value'] == '1262':
        fall_2025_26 = term
        break

if not fall_2025_26:
    print('❌ Could not find Fall 2025-26 term')
    scraper.driver.quit()
    sys.exit(1)

print(f'✅ Found term: {fall_2025_26["text"]} (code: {fall_2025_26["value"]})')
print(f'⏳ Scraping courses... (this may take 10-15 minutes)')

# Scrape the term
courses_count = scraper.scrape_term(fall_2025_26)

if courses_count > 0:
    print(f'✅ Scraped {courses_count} courses')

    # Get new data
    new_df = pd.DataFrame(scraper.all_courses)

    # Load existing data
    existing_df = pd.read_csv('princeton/princeton_enrollment.csv')

    # Remove old Fall 2025-26 data
    print(f'📊 Updating CSV file...')
    old_count = len(existing_df[existing_df['term_text'] == '25-26 Fall'])
    print(f'   Removing {old_count} old courses')
    existing_df = existing_df[existing_df['term_text'] != '25-26 Fall']

    # Add new data
    print(f'   Adding {len(new_df)} new courses')
    updated_df = pd.concat([existing_df, new_df], ignore_index=True)

    # Sort by term and course code
    updated_df = updated_df.sort_values(['term_value', 'course_code'])

    # Save
    updated_df.to_csv('princeton/princeton_enrollment.csv', index=False)
    print(f'✅ Updated princeton/princeton_enrollment.csv')
    print(f'   Total courses in file: {len(updated_df)}')
else:
    print('❌ No courses scraped')

scraper.driver.quit()
print('✅ Princeton update complete!')
