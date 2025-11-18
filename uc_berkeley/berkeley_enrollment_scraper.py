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

        # Try to get course list from the catalog API
        catalog_url = f"{self.api_base}/catalog/catalog_json/"
        catalog_data = self.get_json(catalog_url)

        if catalog_data:
            logger.info(f"Found {len(catalog_data.get('courses', []))} courses in catalog")
            return catalog_data.get('courses', [])

        # Fallback: scrape from the website
        logger.info("Trying to scrape catalog from website...")
        html = self.get_page(f"{self.base_url}/catalog")

        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        courses = []

        # Extract course links and IDs
        # BerkeleyTime structure may vary, this is a general approach
        for link in soup.find_all('a', href=True):
            if '/catalog/' in link['href']:
                courses.append({
                    'url': link['href'],
                    'text': link.get_text(strip=True)
                })

        logger.info(f"Scraped {len(courses)} course links from catalog")
        return courses

    def get_enrollment_data(self, course_id, semesters=None):
        """
        Get enrollment data for a specific course.

        Args:
            course_id: BerkeleyTime course ID
            semesters: List of semester codes (e.g., ['2024-fall', '2024-spring'])
        """
        # BerkeleyTime enrollment API endpoint pattern
        # This may need adjustment based on actual API structure
        enrollment_url = f"{self.api_base}/enrollment/course/{course_id}/"

        data = self.get_json(enrollment_url)

        if not data:
            return []

        enrollments = []

        # Parse enrollment data structure
        # Exact structure depends on BerkeleyTime API response
        if isinstance(data, list):
            for entry in data:
                enrollments.append(entry)
        elif isinstance(data, dict):
            if 'enrollments' in data:
                enrollments = data['enrollments']
            else:
                enrollments = [data]

        return enrollments

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

    def scrape_all(self, semesters=None):
        """
        Main scraping function.

        Args:
            semesters: List of semester codes to scrape. If None, scrapes recent semesters.
        """
        logger.info("Starting UC Berkeley enrollment scraping...")

        if semesters is None:
            # Default to recent semesters
            semesters = [
                '2024-fall', '2024-spring',
                '2023-fall', '2023-spring',
                '2022-fall', '2022-spring',
                '2021-fall', '2021-spring',
                '2020-fall', '2020-spring'
            ]

        logger.info(f"Scraping {len(semesters)} semesters")

        for semester in semesters:
            try:
                self.scrape_semester(semester)
                time.sleep(2)  # Respectful delay
            except Exception as e:
                logger.error(f"Error scraping semester {semester}: {e}")
                self.stats['errors'] += 1

        logger.info(f"Scraping complete! Total courses: {self.stats['total_courses']}")
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
    scraper = BerkeleyTimeScraperAPI()

    print("\n" + "="*60)
    print("UC BERKELEY ENROLLMENT SCRAPER (BerkeleyTime)")
    print("="*60)
    print("\nNOTE: BerkeleyTime aggregates data from Berkeley SIS.")
    print("This scraper will attempt to access their public data.")
    print("\nOptions:")
    print("1. Try API endpoints (recommended)")
    print("2. Scrape web pages (fallback)")
    print("="*60)

    # Try API method first
    print("\nAttempting API method...")
    scraper.scrape_all()

    # If no data, try web scraping
    if not scraper.courses_data:
        print("\nAPI method yielded no data. Trying web scraping...")
        scraper.scrape_via_web_pages()

    # Save results
    scraper.save_results()

if __name__ == "__main__":
    main()
