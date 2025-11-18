#!/usr/bin/env python3
"""
UW-Madison Enrollment Scraper using Madgrades Data

This scraper accesses Madgrades which provides UW-Madison grade distributions
and enrollment data from 2006 to present.

Data sources:
- Website: https://madgrades.com/
- Kaggle: https://www.kaggle.com/datasets/Madgrades/uw-madison-courses
- GitHub: https://github.com/Madgrades/madgrades-data
- Official: https://registrar.wisc.edu/grade-reports/

Note: Data is also available as a Kaggle dataset which may be easier to download directly.
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
        logging.FileHandler('madison_scraper.log', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MadgradesScraperAPI:
    """UW-Madison enrollment scraper using Madgrades and ScraperAPI."""

    def __init__(self):
        self.api_key = os.environ.get('SCRAPER_API_KEY', '')
        if not self.api_key:
            logger.warning("No SCRAPER_API_KEY found. Using direct requests.")

        self.base_url = "https://madgrades.com"
        self.registrar_url = "https://registrar.wisc.edu/grade-reports/"
        self.scraper_api_url = "http://api.scraperapi.com"

        # Output directory
        self.output_dir = os.path.dirname(os.path.abspath(__file__))

        # Data storage
        self.courses_data = []
        self.grade_distributions = []
        self.stats = {'total_courses': 0, 'terms_processed': 0, 'errors': 0}

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

    def scrape_course_page(self, course_url):
        """Scrape individual course page from Madgrades."""
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

        # Extract course code
        code_match = re.search(r'/courses/([A-Z]+)/(\d+)', course_url)
        if code_match:
            course_data['subject'] = code_match.group(1)
            course_data['course_number'] = code_match.group(2)
            course_data['course_code'] = f"{code_match.group(1)} {code_match.group(2)}"

        # Extract grade distribution tables
        tables = soup.find_all('table')
        grade_data = []

        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 3:
                    row_data = [col.get_text(strip=True) for col in cols]
                    grade_data.append(row_data)

        if grade_data:
            course_data['grade_distributions'] = grade_data

        # Extract instructor information
        instructors = soup.find_all(text=re.compile(r'Instructor', re.I))
        if instructors:
            course_data['has_instructor_data'] = True

        return course_data

    def scrape_subject_courses(self, subject_code):
        """Scrape all courses for a subject."""
        logger.info(f"Scraping subject: {subject_code}")

        subject_url = f"{self.base_url}/courses/{subject_code}"
        html = self.get_page(subject_url)

        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        courses = []

        # Find all course links
        for link in soup.find_all('a', href=True):
            if f'/courses/{subject_code}/' in link['href']:
                course_url = self.base_url + link['href'] if link['href'].startswith('/') else link['href']
                course_name = link.get_text(strip=True)

                courses.append({
                    'url': course_url,
                    'name': course_name,
                    'subject': subject_code
                })

        logger.info(f"Found {len(courses)} courses in {subject_code}")
        return courses

    def get_all_subjects(self):
        """Get list of all subjects/departments."""
        logger.info("Fetching all subjects...")

        html = self.get_page(f"{self.base_url}/subjects")

        if not html:
            # Return common subjects as fallback
            return ['COMP SCI', 'MATH', 'PHYSICS', 'CHEM', 'ECON', 'PSYCH', 'ENGLISH', 'HISTORY']

        soup = BeautifulSoup(html, 'html.parser')
        subjects = []

        # Extract subject links
        for link in soup.find_all('a', href=True):
            if '/courses/' in link['href']:
                match = re.search(r'/courses/([A-Z\s]+)', link['href'])
                if match:
                    subjects.append(match.group(1))

        subjects = list(set(subjects))  # Remove duplicates
        logger.info(f"Found {len(subjects)} subjects")
        return subjects

    def scrape_registrar_pdfs(self):
        """
        Alternative method: Scrape grade report PDFs from official registrar.
        Note: PDFs would need to be parsed separately.
        """
        logger.info("Checking registrar for grade reports...")

        html = self.get_page(self.registrar_url)

        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        pdf_links = []

        # Find all PDF links
        for link in soup.find_all('a', href=True):
            if link['href'].endswith('.pdf'):
                pdf_url = link['href']
                if not pdf_url.startswith('http'):
                    pdf_url = f"https://registrar.wisc.edu{pdf_url}"

                pdf_links.append({
                    'url': pdf_url,
                    'text': link.get_text(strip=True)
                })

        logger.info(f"Found {len(pdf_links)} grade report PDFs")
        return pdf_links

    def scrape_all(self, subjects=None, max_subjects=None):
        """
        Main scraping function.

        Args:
            subjects: List of subject codes to scrape. If None, scrapes all.
            max_subjects: Maximum number of subjects to scrape (for testing).
        """
        logger.info("Starting UW-Madison enrollment scraping...")

        if subjects is None:
            subjects = self.get_all_subjects()

        if max_subjects:
            subjects = subjects[:max_subjects]
            logger.info(f"Limiting to {max_subjects} subjects for testing")

        logger.info(f"Scraping {len(subjects)} subjects")

        for subject in subjects:
            try:
                # Get all courses in subject
                courses = self.scrape_subject_courses(subject)

                # Scrape each course (limit for testing)
                for i, course in enumerate(courses[:5]):  # Limit to 5 per subject for testing
                    try:
                        course_data = self.scrape_course_page(course['url'])
                        if course_data:
                            self.courses_data.append(course_data)
                            self.stats['total_courses'] += 1

                        time.sleep(1)  # Respectful delay
                    except Exception as e:
                        logger.error(f"Error scraping course {course['url']}: {e}")
                        self.stats['errors'] += 1

                time.sleep(2)  # Delay between subjects

            except Exception as e:
                logger.error(f"Error processing subject {subject}: {e}")
                self.stats['errors'] += 1

        logger.info(f"Scraping complete! Total courses: {self.stats['total_courses']}")
        return self.courses_data

    def download_kaggle_dataset_instructions(self):
        """
        Print instructions for downloading the Kaggle dataset.
        This is often easier than scraping.
        """
        print("\n" + "="*70)
        print("KAGGLE DATASET DOWNLOAD INSTRUCTIONS")
        print("="*70)
        print("\nThe UW-Madison data is available on Kaggle (2006-2017):")
        print("https://www.kaggle.com/datasets/Madgrades/uw-madison-courses")
        print("\nTo download:")
        print("1. Create a Kaggle account at https://www.kaggle.com")
        print("2. Install kaggle CLI: pip install kaggle")
        print("3. Download API token from https://www.kaggle.com/account")
        print("4. Run: kaggle datasets download -d Madgrades/uw-madison-courses")
        print("\nAlternatively, download manually from the website.")
        print("="*70)

    def save_results(self):
        """Save results to CSV and JSON."""
        if not self.courses_data:
            logger.warning("No data to save")
            return

        # Save CSV
        df = pd.DataFrame(self.courses_data)
        csv_file = Path(self.output_dir) / 'madison_enrollment.csv'
        df.to_csv(csv_file, index=False)
        logger.info(f"Saved {len(df)} courses to {csv_file}")

        # Save JSON
        json_file = Path(self.output_dir) / 'madison_enrollment.json'
        with open(json_file, 'w') as f:
            json.dump(self.courses_data, f, indent=2)

        # Print summary
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE - UW-MADISON")
        print(f"{'='*60}")
        print(f"Total courses: {self.stats['total_courses']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"{'='*60}")

def main():
    """Main entry point."""
    scraper = MadgradesScraperAPI()

    print("\n" + "="*70)
    print("UW-MADISON ENROLLMENT SCRAPER (Madgrades)")
    print("="*70)
    print("\nData from 2006-present available!")
    print("\nOptions:")
    print("1. Download Kaggle dataset (easiest - 2006-2017 data)")
    print("2. Scrape Madgrades.com (current data)")
    print("3. Download PDFs from registrar (requires PDF parsing)")
    print("="*70)

    choice = input("\nEnter choice (1/2/3) or press Enter to scrape: ").strip()

    if choice == '1':
        scraper.download_kaggle_dataset_instructions()
    elif choice == '3':
        pdf_links = scraper.scrape_registrar_pdfs()
        print(f"\nFound {len(pdf_links)} PDF reports")
        print("Note: PDF parsing not implemented in this scraper.")
    else:
        # Run scraper (limited for testing)
        print("\nStarting scraper (limited mode for testing)...")
        scraper.scrape_all(max_subjects=3)
        scraper.save_results()

if __name__ == "__main__":
    main()
