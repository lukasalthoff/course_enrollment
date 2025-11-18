#!/usr/bin/env python3
"""
UCLA Enrollment Scraper using Hotseat

This scraper accesses Hotseat.io which provides UCLA course enrollment data,
grade distributions, and professor reviews.

Data source: https://hotseat.io/
Data from: 2+ years (since June 2021)
Official source: Integrates data directly from UCLA Registrar

Hotseat tracks enrollment trends and provides historical enrollment progress charts.
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
        logging.FileHandler('ucla_scraper.log', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HotseatScraperAPI:
    """UCLA enrollment scraper using Hotseat and ScraperAPI."""

    def __init__(self):
        self.api_key = os.environ.get('SCRAPER_API_KEY', '')
        if not self.api_key:
            logger.warning("No SCRAPER_API_KEY found. Using direct requests.")

        self.base_url = "https://hotseat.io"
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
                'render': 'true',  # May need rendering for dynamic content
                'country_code': 'us'
            }

            for attempt in range(retries):
                try:
                    response = requests.get(self.scraper_api_url, params=params, timeout=90)
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

    def scrape_course_page(self, course_url):
        """Scrape individual course page from Hotseat."""
        logger.info(f"Scraping course: {course_url}")

        html = self.get_page(course_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        course_data = {
            'url': course_url,
            'scraped_at': datetime.now().isoformat()
        }

        # Extract course title
        title = soup.find('h1')
        if title:
            course_data['course_title'] = title.get_text(strip=True)

        # Extract course code from URL
        code_match = re.search(r'/courses/(\d+)', course_url)
        if code_match:
            course_data['course_id'] = code_match.group(1)

        # Extract enrollment information
        # Hotseat displays enrollment charts and statistics
        enrollment_divs = soup.find_all(['div', 'span'], text=re.compile(r'enroll', re.I))
        for div in enrollment_divs:
            text = div.get_text()
            # Look for enrollment numbers
            numbers = re.findall(r'\d+', text)
            if numbers:
                course_data['enrollment_info'] = text

        # Extract grade distribution
        grade_elements = soup.find_all(text=re.compile(r'grade|GPA', re.I))
        if grade_elements:
            course_data['has_grade_data'] = True

        # Extract instructor information
        instructor_elements = soup.find_all(['div', 'span', 'a'], text=re.compile(r'professor|instructor', re.I))
        instructors = []
        for elem in instructor_elements:
            # Try to find instructor names
            links = elem.find_all('a') if hasattr(elem, 'find_all') else []
            for link in links:
                if '/instructors/' in link.get('href', ''):
                    instructors.append(link.get_text(strip=True))

        if instructors:
            course_data['instructors'] = instructors

        # Extract reviews count
        reviews = soup.find_all(text=re.compile(r'review', re.I))
        if reviews:
            for review_text in reviews:
                review_match = re.search(r'(\d+)\s*reviews?', review_text, re.I)
                if review_match:
                    course_data['review_count'] = int(review_match.group(1))
                    break

        return course_data

    def get_all_departments(self):
        """Get list of all departments."""
        logger.info("Fetching all departments...")

        # Try departments page
        html = self.get_page(f"{self.base_url}/departments")

        if not html:
            # Return common UCLA departments as fallback
            return ['Computer Science', 'Mathematics', 'Economics', 'Psychology',
                    'Engineering', 'Chemistry', 'Physics', 'English']

        soup = BeautifulSoup(html, 'html.parser')
        departments = []

        # Find department links
        for link in soup.find_all('a', href=True):
            if '/departments/' in link['href']:
                dept_name = link.get_text(strip=True)
                if dept_name and len(dept_name) > 2:
                    departments.append({
                        'name': dept_name,
                        'url': self.base_url + link['href'] if link['href'].startswith('/') else link['href']
                    })

        departments = {dept['name']: dept for dept in departments}.values()  # Remove duplicates
        departments = list(departments)

        logger.info(f"Found {len(departments)} departments")
        return departments

    def scrape_department_courses(self, dept_url, dept_name):
        """Scrape all courses in a department."""
        logger.info(f"Scraping department: {dept_name}")

        html = self.get_page(dept_url)

        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        courses = []

        # Find course links
        for link in soup.find_all('a', href=True):
            if '/courses/' in link['href'] and re.search(r'/courses/\d+', link['href']):
                course_url = self.base_url + link['href'] if link['href'].startswith('/') else link['href']
                course_name = link.get_text(strip=True)

                courses.append({
                    'url': course_url,
                    'name': course_name,
                    'department': dept_name
                })

        # Remove duplicates
        courses = {c['url']: c for c in courses}.values()
        courses = list(courses)

        logger.info(f"Found {len(courses)} courses in {dept_name}")
        return courses

    def scrape_trending_courses(self):
        """Scrape trending/popular courses from homepage."""
        logger.info("Scraping trending courses...")

        html = self.get_page(self.base_url)

        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        courses = []

        # Look for trending or featured courses
        for link in soup.find_all('a', href=True):
            if '/courses/' in link['href']:
                course_url = self.base_url + link['href'] if link['href'].startswith('/') else link['href']
                courses.append(course_url)

        courses = list(set(courses))  # Remove duplicates
        logger.info(f"Found {len(courses)} trending courses")
        return courses

    def scrape_all(self, max_departments=None, max_courses_per_dept=None):
        """
        Main scraping function.

        Args:
            max_departments: Maximum number of departments to scrape (for testing).
            max_courses_per_dept: Maximum courses per department (for testing).
        """
        logger.info("Starting UCLA enrollment scraping via Hotseat...")

        # Get departments
        departments = self.get_all_departments()

        if max_departments:
            departments = departments[:max_departments]
            logger.info(f"Limiting to {max_departments} departments for testing")

        logger.info(f"Scraping {len(departments)} departments")

        for dept in departments:
            try:
                # Get courses in department
                courses = self.scrape_department_courses(dept['url'], dept['name'])

                if max_courses_per_dept:
                    courses = courses[:max_courses_per_dept]

                # Scrape each course
                for course in courses:
                    try:
                        course_data = self.scrape_course_page(course['url'])
                        if course_data:
                            course_data['department'] = dept['name']
                            self.courses_data.append(course_data)
                            self.stats['total_courses'] += 1

                        time.sleep(2)  # Respectful delay

                    except Exception as e:
                        logger.error(f"Error scraping course {course['url']}: {e}")
                        self.stats['errors'] += 1

                self.stats['departments_processed'] += 1
                time.sleep(3)  # Delay between departments

            except Exception as e:
                logger.error(f"Error processing department {dept['name']}: {e}")
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
        csv_file = Path(self.output_dir) / 'ucla_enrollment.csv'
        df.to_csv(csv_file, index=False)
        logger.info(f"Saved {len(df)} courses to {csv_file}")

        # Save JSON
        json_file = Path(self.output_dir) / 'ucla_enrollment.json'
        with open(json_file, 'w') as f:
            json.dump(self.courses_data, f, indent=2)

        # Print summary
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE - UCLA (Hotseat)")
        print(f"{'='*60}")
        print(f"Total courses: {self.stats['total_courses']}")
        print(f"Departments processed: {self.stats['departments_processed']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"{'='*60}")

def main():
    """Main entry point."""
    scraper = HotseatScraperAPI()

    print("\n" + "="*60)
    print("UCLA ENROLLMENT SCRAPER (Hotseat)")
    print("="*60)
    print("\nData from Hotseat.io - UCLA's course enrollment tracker")
    print("Includes enrollment trends, grades, and reviews")
    print("="*60)

    # Run scraper (limited for testing)
    print("\nStarting scraper (limited mode for testing)...")
    scraper.scrape_all(max_departments=3, max_courses_per_dept=5)
    scraper.save_results()

if __name__ == "__main__":
    main()
