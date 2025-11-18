#!/usr/bin/env python3
"""
UC San Diego Enrollment Scraper using CAPE

This scraper accesses CAPE (Course And Professor Evaluations) which provides
UCSD course evaluation data with enrollment information.

Data source: https://cape.ucsd.edu/
Data from: Spring 2007 to Spring 2021 (14 years)
Data type: Course evaluations with enrollment context, professor ratings

CAPE is a student-run organization. Numerical results are publicly accessible.
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
        logging.FileHandler('ucsd_scraper.log', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CAPEScraperAPI:
    """UCSD enrollment scraper using CAPE and ScraperAPI."""

    def __init__(self):
        self.api_key = os.environ.get('SCRAPER_API_KEY', '')
        if not self.api_key:
            logger.warning("No SCRAPER_API_KEY found. Using direct requests.")

        self.base_url = "https://cape.ucsd.edu"
        self.scraper_api_url = "http://api.scraperapi.com"

        # Output directory
        self.output_dir = os.path.dirname(os.path.abspath(__file__))

        # Data storage
        self.courses_data = []
        self.stats = {'total_courses': 0, 'departments_processed': 0, 'errors': 0}

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

    def get_departments(self):
        """Get list of all departments."""
        logger.info("Fetching departments...")

        # CAPE search/browse page
        html = self.get_page(f"{self.base_url}/responses/")

        if not html:
            # Return common UCSD departments as fallback
            return ['CSE', 'MATH', 'COGS', 'ECON', 'BILD', 'CHEM', 'PHYS', 'ECE']

        soup = BeautifulSoup(html, 'html.parser')
        departments = []

        # Find department options in forms/selects
        selects = soup.find_all('select')
        for select in selects:
            if 'department' in select.get('name', '').lower():
                options = select.find_all('option')
                for option in options:
                    dept_code = option.get('value', '').strip()
                    dept_name = option.get_text(strip=True)
                    if dept_code and dept_code != '':
                        departments.append({
                            'code': dept_code,
                            'name': dept_name
                        })

        if not departments:
            # Try alternative: look for department links
            for link in soup.find_all('a', href=True):
                if 'department=' in link['href'].lower():
                    match = re.search(r'department=([A-Z]+)', link['href'], re.I)
                    if match:
                        departments.append({
                            'code': match.group(1),
                            'name': link.get_text(strip=True)
                        })

        # Remove duplicates
        departments = {d['code']: d for d in departments}.values()
        departments = list(departments)

        logger.info(f"Found {len(departments)} departments")
        return departments

    def scrape_department_evaluations(self, dept_code):
        """Scrape course evaluations for a department."""
        logger.info(f"Scraping department: {dept_code}")

        # CAPE department results page
        dept_url = f"{self.base_url}/responses/Results.aspx?dept={dept_code}"

        html = self.get_page(dept_url)

        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        courses = []

        # Find evaluation tables
        tables = soup.find_all('table')

        for table in tables:
            rows = table.find_all('tr')

            for row in rows:
                cols = row.find_all(['td', 'th'])

                if len(cols) < 3:
                    continue

                course_data = {
                    'department': dept_code,
                    'scraped_at': datetime.now().isoformat()
                }

                # Extract column data
                col_texts = [col.get_text(strip=True) for col in cols]

                # Try to identify columns
                for i, text in enumerate(col_texts):
                    # Course code
                    if re.match(r'[A-Z]+\s*\d+[A-Z]*', text):
                        course_data['course_code'] = text

                    # Instructor
                    if i > 0 and re.search(r'[A-Z][a-z]+,\s*[A-Z]', text):
                        course_data['instructor'] = text

                    # Term/Quarter
                    if re.search(r'(FA|WI|SP|S[123])\s*\d{2}', text):
                        course_data['term'] = text

                    # Enrollment count
                    if re.match(r'^\d+$', text) and 'Enroll' in str(cols[i]):
                        course_data['enrollment'] = int(text)

                    # Evaluations Made
                    if re.match(r'^\d+$', text) and 'Evals' in str(cols[i]):
                        course_data['evaluations_made'] = int(text)

                    # Recommended (percentage)
                    if '%' in text:
                        percent_match = re.search(r'(\d+\.?\d*)%', text)
                        if percent_match:
                            course_data['recommend_pct'] = float(percent_match.group(1))

                    # GPA
                    if re.match(r'^\d\.\d+$', text):
                        try:
                            gpa = float(text)
                            if 0 <= gpa <= 4.0:
                                course_data['avg_gpa'] = gpa
                        except:
                            pass

                if 'course_code' in course_data:
                    courses.append(course_data)

        logger.info(f"Found {len(courses)} evaluations in {dept_code}")
        return courses

    def scrape_search_results(self, search_term=None):
        """Scrape CAPE search results."""
        logger.info(f"Searching for: {search_term or 'all courses'}")

        # CAPE search page
        search_url = f"{self.base_url}/responses/Results.aspx"

        if search_term:
            search_url += f"?Name={search_term}"

        html = self.get_page(search_url)

        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        results = []

        # Parse results similar to department scraping
        tables = soup.find_all('table')

        for table in tables:
            # Extract evaluation data
            rows = table.find_all('tr')

            for row in rows:
                data = self.parse_evaluation_row(row)
                if data:
                    results.append(data)

        return results

    def parse_evaluation_row(self, row):
        """Parse individual evaluation row."""
        cols = row.find_all(['td', 'th'])

        if len(cols) < 3:
            return None

        data = {
            'scraped_at': datetime.now().isoformat()
        }

        # Extract data from each column
        for col in cols:
            text = col.get_text(strip=True)

            # Course code
            if re.match(r'[A-Z]+\s*\d+', text) and 'course_code' not in data:
                data['course_code'] = text

            # Look for numbers
            if re.match(r'^\d+$', text):
                # Could be enrollment or evaluations
                if 'enrollment' not in data:
                    data['enrollment'] = int(text)
                elif 'evaluations_made' not in data:
                    data['evaluations_made'] = int(text)

        return data if 'course_code' in data else None

    def scrape_statistics_page(self):
        """Scrape CAPE statistics overview page."""
        logger.info("Scraping statistics page...")

        stats_url = f"{self.base_url}/scripts/stats.asp"

        html = self.get_page(stats_url)

        if not html:
            return {}

        soup = BeautifulSoup(html, 'html.parser')

        stats = {
            'scraped_at': datetime.now().isoformat()
        }

        # Extract overall statistics
        # This page typically shows aggregate data

        # Look for tables with statistics
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 2:
                    label = cols[0].get_text(strip=True)
                    value = cols[1].get_text(strip=True)
                    stats[label] = value

        return stats

    def scrape_all(self, departments=None, max_departments=None):
        """
        Main scraping function.

        Args:
            departments: List of department codes to scrape. If None, scrapes all.
            max_departments: Maximum number of departments to scrape (for testing).
        """
        logger.info("Starting UCSD CAPE scraping...")

        if departments is None:
            departments = self.get_departments()

        if max_departments:
            departments = departments[:max_departments]
            logger.info(f"Limiting to {max_departments} departments for testing")

        logger.info(f"Scraping {len(departments)} departments")

        for dept in departments:
            try:
                dept_code = dept['code'] if isinstance(dept, dict) else dept

                # Scrape department evaluations
                courses = self.scrape_department_evaluations(dept_code)
                self.courses_data.extend(courses)

                self.stats['total_courses'] += len(courses)
                self.stats['departments_processed'] += 1

                time.sleep(2)  # Respectful delay

            except Exception as e:
                logger.error(f"Error processing department {dept_code}: {e}")
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
        csv_file = Path(self.output_dir) / 'ucsd_enrollment.csv'
        df.to_csv(csv_file, index=False)
        logger.info(f"Saved {len(df)} courses to {csv_file}")

        # Save JSON
        json_file = Path(self.output_dir) / 'ucsd_enrollment.json'
        with open(json_file, 'w') as f:
            json.dump(self.courses_data, f, indent=2)

        # Print summary
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE - UCSD (CAPE)")
        print(f"{'='*60}")
        print(f"Total courses: {self.stats['total_courses']}")
        print(f"Departments processed: {self.stats['departments_processed']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"{'='*60}")

def main():
    """Main entry point."""
    scraper = CAPEScraperAPI()

    print("\n" + "="*60)
    print("UCSD ENROLLMENT SCRAPER (CAPE)")
    print("="*60)
    print("\nCourse And Professor Evaluations")
    print("Data from 2007-2021 (14 years)")
    print("Includes enrollment, evaluations, GPAs, recommendations")
    print("="*60)

    # Run scraper (limited for testing)
    print("\nStarting scraper (limited mode for testing)...")
    scraper.scrape_all(max_departments=3)
    scraper.save_results()

if __name__ == "__main__":
    main()
