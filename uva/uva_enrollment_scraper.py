#!/usr/bin/env python3
"""
University of Virginia Enrollment Scraper using Lou's List / Hoos' List

This scraper accesses UVA's course enrollment data from Lou's List (legacy)
and the new Hoos' List platform.

Data sources:
- Lou's List: https://louslist.org/ (legacy, still functional)
- Hoos' List: https://hooslist.virginia.edu/ (official UVA platform)
- Data: Enrollment, waitlist, capacity for courses from 2018-present

Both sites mine data from UVA's Student Information System (SIS).
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
        logging.FileHandler('uva_scraper.log', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UVAEnrollmentScraperAPI:
    """UVA enrollment scraper using Lou's List/Hoos' List and ScraperAPI."""

    def __init__(self, use_hooslist=False):
        self.api_key = os.environ.get('SCRAPER_API_KEY', '')
        if not self.api_key:
            logger.warning("No SCRAPER_API_KEY found. Using direct requests.")

        # Choose between Lou's List and Hoos' List
        if use_hooslist:
            self.base_url = "https://hooslist.virginia.edu"
            self.platform = "Hoos' List"
        else:
            self.base_url = "https://louslist.org"
            self.platform = "Lou's List"

        self.scraper_api_url = "http://api.scraperapi.com"

        # Output directory
        self.output_dir = os.path.dirname(os.path.abspath(__file__))

        # Data storage
        self.courses_data = []
        self.stats = {'total_courses': 0, 'semesters_processed': 0, 'errors': 0}

        # Semester code mappings (Lou's List format: 1248 = Fall 2024, 1252 = Spring 2025)
        self.semesters = self.generate_semester_codes()

    def get_page(self, url, retries=3):
        """Fetch page using ScraperAPI or direct request."""
        if self.api_key:
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
                        logger.warning("Rate limit reached, waiting...")
                        time.sleep(10)
                except Exception as e:
                    logger.error(f"ScraperAPI error: {e}")
        else:
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

    def generate_semester_codes(self):
        """
        Generate UVA semester codes.
        Format: 1YYS where YY is year (24 = 2024) and S is semester (2=spring, 8=fall)
        Example: 1248 = Fall 2024, 1252 = Spring 2025
        """
        semesters = []

        # Generate codes from 2018 to 2025
        for year in range(18, 26):  # 2018-2025
            semesters.append({
                'code': f'12{year}8',
                'name': f'Fall 20{year}',
                'year': f'20{year}',
                'term': 'Fall'
            })
            semesters.append({
                'code': f'12{year+1}2',
                'name': f'Spring 20{year+1}',
                'year': f'20{year+1}',
                'term': 'Spring'
            })

        return semesters

    def scrape_semester(self, semester_code, semester_name):
        """Scrape all courses for a specific semester."""
        logger.info(f"Scraping {semester_name} (code: {semester_code})")

        # Lou's List URL pattern
        semester_url = f"{self.base_url}/?Semester={semester_code}"

        html = self.get_page(semester_url)

        if not html:
            logger.error(f"Failed to fetch data for {semester_name}")
            return []

        soup = BeautifulSoup(html, 'html.parser')
        courses = []

        # Find course tables
        tables = soup.find_all('table')

        for table in tables:
            rows = table.find_all('tr')

            for row in rows:
                cols = row.find_all(['td', 'th'])

                if len(cols) >= 5:  # Typical course row has multiple columns
                    course_data = {
                        'semester_code': semester_code,
                        'semester_name': semester_name,
                        'scraped_at': datetime.now().isoformat()
                    }

                    # Extract text from columns
                    col_texts = [col.get_text(strip=True) for col in cols]

                    # Try to identify course code
                    for text in col_texts:
                        if re.match(r'[A-Z]{2,4}\s*\d{4}', text):
                            course_data['course_code'] = text
                            break

                    # Extract enrollment information
                    for text in col_texts:
                        # Look for enrollment patterns like "45 / 60" or "Enrolled: 45"
                        enrollment_match = re.search(r'(\d+)\s*/\s*(\d+)', text)
                        if enrollment_match:
                            course_data['enrolled'] = int(enrollment_match.group(1))
                            course_data['capacity'] = int(enrollment_match.group(2))

                        # Look for waitlist
                        waitlist_match = re.search(r'Wait(?:list)?:\s*(\d+)', text, re.I)
                        if waitlist_match:
                            course_data['waitlist'] = int(waitlist_match.group(1))

                    # Extract instructor
                    for col in cols:
                        # Instructor columns often have specific classes or patterns
                        if 'instructor' in col.get('class', []):
                            course_data['instructor'] = col.get_text(strip=True)

                    # Only add if we found a course code
                    if 'course_code' in course_data:
                        courses.append(course_data)

        # Alternative parsing: Look for specific div/span structures
        if not courses:
            logger.info("Trying alternative parsing method...")
            courses = self.parse_alternative_structure(soup, semester_code, semester_name)

        logger.info(f"Found {len(courses)} courses in {semester_name}")
        self.stats['total_courses'] += len(courses)
        self.stats['semesters_processed'] += 1

        return courses

    def parse_alternative_structure(self, soup, semester_code, semester_name):
        """Alternative parsing method for different HTML structures."""
        courses = []

        # Look for course links
        for link in soup.find_all('a', href=True):
            # Course detail links
            if 'courseCode=' in link['href'] or 'class.php' in link['href']:
                course_data = {
                    'semester_code': semester_code,
                    'semester_name': semester_name,
                    'course_link': link['href'],
                    'scraped_at': datetime.now().isoformat()
                }

                # Extract course code from link text or href
                link_text = link.get_text(strip=True)
                code_match = re.match(r'([A-Z]{2,4}\s*\d{4})', link_text)
                if code_match:
                    course_data['course_code'] = code_match.group(1)

                # Look for enrollment in nearby elements
                parent = link.parent
                if parent:
                    parent_text = parent.get_text()
                    enrollment_match = re.search(r'(\d+)\s*/\s*(\d+)', parent_text)
                    if enrollment_match:
                        course_data['enrolled'] = int(enrollment_match.group(1))
                        course_data['capacity'] = int(enrollment_match.group(2))

                if 'course_code' in course_data:
                    courses.append(course_data)

        return courses

    def scrape_subject(self, subject_code, semester_code):
        """Scrape courses for a specific subject in a semester."""
        # Lou's List subject URL pattern
        subject_url = f"{self.base_url}/page.php?Semester={semester_code}&Type=Subject&Subject={subject_code}"

        html = self.get_page(subject_url)

        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        courses = []

        # Parse subject page
        tables = soup.find_all('table')

        for table in tables:
            rows = table.find_all('tr')

            for row in rows:
                course_data = self.parse_course_row(row, semester_code)
                if course_data:
                    course_data['subject'] = subject_code
                    courses.append(course_data)

        return courses

    def parse_course_row(self, row, semester_code):
        """Parse individual course row."""
        cols = row.find_all(['td', 'th'])

        if len(cols) < 3:
            return None

        course_data = {
            'semester_code': semester_code,
            'scraped_at': datetime.now().isoformat()
        }

        # Extract all column texts
        for i, col in enumerate(cols):
            text = col.get_text(strip=True)

            # Course code
            if re.match(r'[A-Z]{2,4}\s*\d{4}', text):
                course_data['course_code'] = text

            # Section
            if re.match(r'^\d{3}$', text):
                course_data['section'] = text

            # Enrollment
            if '/' in text and re.search(r'\d+\s*/\s*\d+', text):
                match = re.search(r'(\d+)\s*/\s*(\d+)', text)
                course_data['enrolled'] = int(match.group(1))
                course_data['capacity'] = int(match.group(2))

        return course_data if 'course_code' in course_data else None

    def scrape_all(self, semesters=None, max_semesters=None):
        """
        Main scraping function.

        Args:
            semesters: List of semester dicts to scrape. If None, uses recent semesters.
            max_semesters: Maximum number of semesters to scrape (for testing).
        """
        logger.info(f"Starting UVA enrollment scraping using {self.platform}...")

        if semesters is None:
            semesters = self.semesters

        if max_semesters:
            semesters = semesters[:max_semesters]
            logger.info(f"Limiting to {max_semesters} semesters for testing")

        logger.info(f"Scraping {len(semesters)} semesters")

        for semester in semesters:
            try:
                courses = self.scrape_semester(semester['code'], semester['name'])
                self.courses_data.extend(courses)

                time.sleep(3)  # Respectful delay between semesters

            except Exception as e:
                logger.error(f"Error scraping {semester['name']}: {e}")
                self.stats['errors'] += 1

        logger.info(f"Scraping complete! Total courses: {self.stats['total_courses']}")
        return self.courses_data

    def save_results(self):
        """Save results to CSV and JSON."""
        if not self.courses_data:
            logger.warning("No data to save")
            return

        # Save CSV
        df = pd.DataFrame(self.courses_data)
        csv_file = Path(self.output_dir) / 'uva_enrollment.csv'
        df.to_csv(csv_file, index=False)
        logger.info(f"Saved {len(df)} courses to {csv_file}")

        # Save JSON
        json_file = Path(self.output_dir) / 'uva_enrollment.json'
        with open(json_file, 'w') as f:
            json.dump(self.courses_data, f, indent=2)

        # Print summary
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE - UVA ({self.platform})")
        print(f"{'='*60}")
        print(f"Total courses: {self.stats['total_courses']}")
        print(f"Semesters processed: {self.stats['semesters_processed']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"{'='*60}")

def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("UVA ENROLLMENT SCRAPER")
    print("="*60)
    print("\nChoose data source:")
    print("1. Lou's List (legacy, still works) - https://louslist.org")
    print("2. Hoos' List (official UVA) - https://hooslist.virginia.edu")
    print("="*60)

    choice = input("\nEnter choice (1/2) or press Enter for Lou's List: ").strip()

    use_hooslist = (choice == '2')
    scraper = UVAEnrollmentScraperAPI(use_hooslist=use_hooslist)

    # Run scraper (limited for testing)
    print(f"\nStarting scraper using {scraper.platform}...")
    scraper.scrape_all(max_semesters=4)  # Test with 4 semesters
    scraper.save_results()

if __name__ == "__main__":
    main()
