#!/usr/bin/env python3
"""
Script to update Fall 2025-26 enrollment data for all universities.
This updates only the Fall 2025-26 term to minimize load on university servers.
"""

import sys
import os
import pandas as pd
from datetime import datetime

# Add subdirectories to path
sys.path.append('princeton')
sys.path.append('stanford')

def update_princeton_fall_2025_26():
    """Update Princeton Fall 2025-26 data"""
    print("\n" + "="*60)
    print("PRINCETON: Updating Fall 2025-26 Enrollment Data")
    print("="*60)

    try:
        from princeton_enrollment_scraper import PrincetonFixedScraper
        import time
        import random

        scraper = PrincetonFixedScraper()

        if not scraper.setup_browser():
            print("❌ Failed to setup browser")
            return False

        # Get available terms
        available_terms = scraper.get_available_terms()

        # Find Fall 2025-26 term (term code 1262)
        fall_2025_26_term = None
        for term in available_terms:
            if '25-26 Fall' in term['text'] or term['value'] == '1262':
                fall_2025_26_term = term
                break

        if not fall_2025_26_term:
            print("❌ Could not find Fall 2025-26 term")
            scraper.driver.quit()
            return False

        print(f"✅ Found term: {fall_2025_26_term['text']} (code: {fall_2025_26_term['value']})")

        # Scrape just this term
        courses_scraped = scraper.scrape_term(fall_2025_26_term)

        if courses_scraped > 0:
            # Get the new data
            new_df = pd.DataFrame(scraper.all_courses)

            # Load existing data
            existing_df = pd.read_csv('princeton/princeton_enrollment.csv')

            # Remove old Fall 2025-26 data
            print(f"\n📊 Removing old Fall 2025-26 data...")
            old_count = len(existing_df[existing_df['term_text'] == '25-26 Fall'])
            print(f"   Old data: {old_count} courses")
            existing_df = existing_df[existing_df['term_text'] != '25-26 Fall']

            # Add new data
            print(f"   New data: {len(new_df)} courses")
            updated_df = pd.concat([existing_df, new_df], ignore_index=True)

            # Sort by term and course code
            updated_df = updated_df.sort_values(['term_value', 'course_code'])

            # Save
            updated_df.to_csv('princeton/princeton_enrollment.csv', index=False)
            print(f"✅ Updated princeton/princeton_enrollment.csv")
            print(f"   Total courses in file: {len(updated_df)}")

            scraper.driver.quit()
            return True
        else:
            print("❌ No courses scraped")
            scraper.driver.quit()
            return False

    except Exception as e:
        print(f"❌ Error updating Princeton data: {e}")
        import traceback
        traceback.print_exc()
        return False

def update_stanford_fall_2025():
    """Update Stanford Fall 2025 data (academic year 2025-2026)"""
    print("\n" + "="*60)
    print("STANFORD: Updating Fall 2025 Enrollment Data")
    print("="*60)

    print("⚠️  Stanford scraper requires SCRAPER_API_KEY environment variable")
    print("    Checking for API key...")

    if not os.environ.get('SCRAPER_API_KEY'):
        print("❌ No SCRAPER_API_KEY found")
        print("    Stanford has anti-scraping measures that require a proxy service")
        print("    Skipping Stanford update - please set SCRAPER_API_KEY to update")
        return False

    try:
        from stanford_enrollment_scraper import StanfordScraperAPI

        scraper = StanfordScraperAPI()

        # For Stanford, we need to scrape the 2025-2026 academic year
        # which includes Fall 2025 (starts Sept 2025)
        # Since the scraper may take a long time, we'll skip this for now
        # and notify the user

        print("ℹ️  Stanford scraper will scrape entire academic year 2025-2026")
        print("    This may take a long time due to rate limiting")
        print("    Skipping for now - run stanford_enrollment_scraper.py manually if needed")

        return False

    except Exception as e:
        print(f"❌ Error updating Stanford data: {e}")
        return False

def update_harvard_fall_2025_26():
    """Check Harvard Fall 2025-26 data"""
    print("\n" + "="*60)
    print("HARVARD: Checking Fall 2025-26 Enrollment Data")
    print("="*60)

    harvard_file = 'harvard/harvard_enrollment_2025_2026_fall.csv'

    if os.path.exists(harvard_file):
        df = pd.read_csv(harvard_file, skiprows=3)  # Skip header rows
        print(f"✅ Harvard Fall 2025-26 data exists")
        print(f"   File: {harvard_file}")
        print(f"   Courses: {len(df)} entries")
        print("\nℹ️  Harvard data is manually downloaded from:")
        print("   https://registrar.fas.harvard.edu/links/archive/enrollment-reports")
        print("   Last generated: April 17, 2025 (from file header)")
        print("   If you need updated data, please download the latest CSV from the URL above")
        return True
    else:
        print(f"❌ Harvard Fall 2025-26 data not found at {harvard_file}")
        return False

def main():
    print("\n" + "="*70)
    print(" UPDATE FALL 2025-26 ENROLLMENT DATA ".center(70, "="))
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {
        'princeton': False,
        'stanford': False,
        'harvard': False
    }

    # Update Princeton
    results['princeton'] = update_princeton_fall_2025_26()

    # Update Stanford (commented out due to complexity)
    # results['stanford'] = update_stanford_fall_2025()
    print("\n" + "="*60)
    print("STANFORD: Manual Update Required")
    print("="*60)
    print("⚠️  Stanford data needs to be updated manually")
    print("    The Stanford scraper requires special setup and takes significant time")
    print("    Current data is from: 2024-2025 academic year")
    print("    Needed: 2025-2026 academic year (includes Fall 2025)")

    # Check Harvard
    results['harvard'] = update_harvard_fall_2025_26()

    # Summary
    print("\n" + "="*70)
    print(" SUMMARY ".center(70, "="))
    print("="*70)
    print(f"Princeton: {'✅ Updated' if results['princeton'] else '❌ Failed'}")
    print(f"Stanford:  ⚠️  Manual update required")
    print(f"Harvard:   {'✅ Current' if results['harvard'] else '❌ Missing'}")
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
