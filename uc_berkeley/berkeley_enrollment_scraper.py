#!/usr/bin/env python3
"""
UC Berkeley Enrollment Scraper using BerkeleyTime Data

This scraper accesses BerkeleyTime's publicly available data which aggregates
enrollment information from Berkeley's Student Information System.

Data source: https://berkeleytime.com/
API: BerkeleyTime uses Berkeley SIS Course and Class APIs

To use ScraperAPI:
1. Sign up at https://www.scraperapi.com (5000 free requests)
2. Set environment variable: export SCRAPER_API_KEY=your_key_here
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import json
import logging
from datetime import datetime
import os
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('berkeley_scraper.log', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BerkeleyTimeScraperAPI:
    """UC Berkeley enrollment scraper using BerkeleyTime and ScraperAPI."""

    def __init__(self):
        self.api_key = os.environ.get('SCRAPER_API_KEY', '')
        if not self.api_key:
            logger.warning("No SCRAPER_API_KEY found. Using direct requests (may be blocked)")

        self.base_url = "https://www.berkeleytime.com"
        self.api_base = "https://www.berkeleytime.com/api"
        self.scraper_api_url = "http://api.scraperapi.com"

        # Output directory
        self.output_dir = os.path.dirname(os.path.abspath(__file__))

        # Data storage
        self.courses_data = []
        self.stats = {'total_courses': 0, 'semesters_processed': 0, 'errors': 0}

    def get_page(self, url, retries=3):
        """Fetch page using ScraperAPI or direct request."""
        if self.api_key:
            # Use ScraperAPI
            params = {
                'api_key': self.api_key,
                'url': url,
                'render': 'false',
                'country_code': 'us'
            }

            for attempt in range(retries):
                try:
                    response = requests.get(self.scraper_api_url, params=params, timeout=60)
                    if response.status_code == 200:
                        return response.text
                    elif response.status_code == 429:
                        logger.warning("Rate limit reached, waiting 10 seconds...")
                        time.sleep(10)
                    else:
                        logger.error(f"ScraperAPI error: {response.status_code}")
                except Exception as e:
                    logger.error(f"Error fetching {url}: {e}")
        else:
            # Direct request
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=30)
                if response.status_code == 200:
                    return response.text
            except Exception as e:
                logger.error(f"Direct request failed: {e}")

        return None

    def get_json(self, url, retries=3):
        """Fetch JSON data from API endpoint."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json'
        }

        for attempt in range(retries):
            try:
                response = requests.get(url, headers=headers, timeout=30)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    logger.warning("Rate limit, waiting...")
                    time.sleep(10)
            except Exception as e:
                logger.error(f"Error fetching JSON from {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)

        return None

    def get_all_courses(self):
        """Get list of all courses from BerkeleyTime catalog."""
        logger.info("Fetching course catalog...")

        # Correct API endpoint based on BerkeleyTime documentation
        catalog_url = f"{self.base_url}/api/catalog/catalog_json/"
        catalog_data = self.get_json(catalog_url)

        if catalog_data:
            # catalog_json returns a list of courses
            courses = catalog_data if isinstance(catalog_data, list) else []
            logger.info(f"Found {len(courses)} courses in catalog")
            return courses

        logger.warning("Failed to fetch catalog from API")
        return []

    def get_enrollment_data(self, course_id, semester, year):
        """
        Get enrollment data for a specific course offering.

        Args:
            course_id: BerkeleyTime course ID
            semester: Semester (e.g., 'fall', 'spring')
            year: Year (e.g., '2024')

        Returns enrollment aggregate data for the specified offering.
        """
        # Correct API endpoint: /api/enrollment/aggregate/{course_id}/{semester}/{year}/
        enrollment_url = f"{self.base_url}/api/enrollment/aggregate/{course_id}/{semester}/{year}/"

        data = self.get_json(enrollment_url)

        if data:
            # Add metadata to the response
            if isinstance(data, dict):
                data['course_id'] = course_id
                data['semester'] = semester
                data['year'] = year

        return data

    def scrape_semester(self, semester_code):
        """
        Scrape enrollment data for a specific semester.

        Args:
            semester_code: Semester identifier (e.g., '2024-fall')
        """
        logger.info(f"Scraping semester: {semester_code}")

        # Get courses offered in this semester
        semester_url = f"{self.api_base}/enrollment/semester/{semester_code}/"
        semester_data = self.get_json(semester_url)

        if not semester_data:
            logger.warning(f"No data found for semester {semester_code}")
            return []

        courses = []

        # Process semester data
        # Structure will depend on actual API response
        if isinstance(semester_data, list):
            courses = semester_data
        elif isinstance(semester_data, dict):
            courses = semester_data.get('courses', [])

        logger.info(f"Found {len(courses)} courses in {semester_code}")

        for course in courses:
            course['semester'] = semester_code
            course['scraped_at'] = datetime.now().isoformat()
            self.courses_data.append(course)

        self.stats['total_courses'] += len(courses)
        self.stats['semesters_processed'] += 1

        return courses

    def scrape_all(self, years=None, semesters=None, max_courses=None):
        """
        Main scraping function using BerkeleyTime API.

        Args:
            years: List of years to scrape (e.g., ['2024', '2023']). Default: recent years.
            semesters: List of semesters (e.g., ['fall', 'spring']). Default: both.
            max_courses: Limit number of courses to scrape (for testing).
        """
        logger.info("Starting UC Berkeley enrollment scraping via BerkeleyTime API...")

        # Default parameters
        if years is None:
            years = ['2024', '2023', '2022', '2021', '2020']
        if semesters is None:
            semesters = ['fall', 'spring']

        logger.info(f"Will scrape {len(years)} years x {len(semesters)} semesters")

        # Step 1: Get all courses from catalog
        logger.info("Step 1: Fetching course catalog...")
        all_courses = self.get_all_courses()

        if not all_courses:
            logger.error("Failed to fetch course catalog!")
            return []

        if max_courses:
            all_courses = all_courses[:max_courses]
            logger.info(f"Limited to {max_courses} courses for testing")

        logger.info(f"Found {len(all_courses)} courses in catalog")

        # Step 2: For each course, get enrollment data for specified semesters
        for i, course in enumerate(all_courses):
            course_id = course.get('id') or course.get('course_id')

            if not course_id:
                logger.warning(f"Course missing ID: {course}")
                continue

            course_code = course.get('abbreviation') or course.get('course_code', 'Unknown')

            if (i + 1) % 10 == 0:
                logger.info(f"Progress: {i+1}/{len(all_courses)} courses processed")

            # Get enrollment for each semester
            for year in years:
                for semester in semesters:
                    try:
                        enrollment_data = self.get_enrollment_data(course_id, semester, year)

                        if enrollment_data:
                            # Combine course info with enrollment data
                            combined_data = {
                                **course,
                                **enrollment_data,
                                'scraped_at': datetime.now().isoformat()
                            }
                            self.courses_data.append(combined_data)
                            self.stats['total_courses'] += 1

                        time.sleep(0.5)  # Small delay between requests

                    except Exception as e:
                        logger.debug(f"No enrollment data for {course_code} {semester} {year}: {e}")
                        self.stats['errors'] += 1

        logger.info(f"Scraping complete! Total course-semester records: {self.stats['total_courses']}")
        return self.courses_data

    def scrape_via_web_pages(self):
        """
        Alternative scraping method using web page scraping.
        Use this if API access doesn't work.
        """
        logger.info("Using web page scraping method...")

        # Get catalog page
        catalog_html = self.get_page(f"{self.base_url}/catalog")

        if not catalog_html:
            logger.error("Failed to fetch catalog page")
            return []

        soup = BeautifulSoup(catalog_html, 'html.parser')

        # Extract course information from HTML
        # This will need to be customized based on BerkeleyTime's actual HTML structure
        courses = []

        # Example: Look for course cards or listings
        course_elements = soup.find_all(['div', 'a'], class_=re.compile(r'course|class', re.I))

        for element in course_elements:
            course_info = {
                'text': element.get_text(strip=True),
                'html': str(element)[:200],  # First 200 chars for debugging
                'scraped_at': datetime.now().isoformat()
            }
            courses.append(course_info)

        logger.info(f"Extracted {len(courses)} course elements from HTML")
        self.courses_data = courses
        return courses

    def save_results(self):
        """Save results to CSV and JSON."""
        if not self.courses_data:
            logger.warning("No data to save")
            return

        # Save CSV
        df = pd.DataFrame(self.courses_data)
        csv_file = Path(self.output_dir) / 'berkeley_enrollment.csv'
        df.to_csv(csv_file, index=False)
        logger.info(f"Saved {len(df)} courses to {csv_file}")

        # Save JSON
        json_file = Path(self.output_dir) / 'berkeley_enrollment.json'
        with open(json_file, 'w') as f:
            json.dump(self.courses_data, f, indent=2)

        # Print summary
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE - UC BERKELEY")
        print(f"{'='*60}")
        print(f"Total courses: {self.stats['total_courses']}")
        print(f"Semesters processed: {self.stats['semesters_processed']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"{'='*60}")

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='UC Berkeley Enrollment Scraper')
    parser.add_argument('--max-courses', type=int, default=10,
                        help='Maximum number of courses to scrape (default: 10 for testing)')
    parser.add_argument('--years', type=str, default='2024,2023',
                        help='Comma-separated years (default: 2024,2023)')
    parser.add_argument('--semesters', type=str, default='fall,spring',
                        help='Comma-separated semesters (default: fall,spring)')
    parser.add_argument('--full', action='store_true',
                        help='Scrape all courses (not just test mode)')

    args = parser.parse_args()

    scraper = BerkeleyTimeScraperAPI()

    print("\n" + "="*70)
    print("UC BERKELEY ENROLLMENT SCRAPER (BerkeleyTime API)")
    print("="*70)
    print("\nUsing BerkeleyTime public API:")
    print("- Catalog API: /api/catalog/catalog_json/")
    print("- Enrollment API: /api/enrollment/aggregate/{id}/{semester}/{year}/")
    print("="*70)

    # Parse arguments
    years = args.years.split(',')
    semesters = args.semesters.split(',')
    max_courses = None if args.full else args.max_courses

    if max_courses:
        print(f"\n⚠️  TEST MODE: Limiting to {max_courses} courses")
        print("Use --full flag to scrape all courses")
    else:
        print("\n🚀 FULL MODE: Scraping all courses")

    print(f"Years: {', '.join(years)}")
    print(f"Semesters: {', '.join(semesters)}")
    print("="*70 + "\n")

    # Run scraper
    scraper.scrape_all(years=years, semesters=semesters, max_courses=max_courses)

    # Save results
    scraper.save_results()

if __name__ == "__main__":
    main()
