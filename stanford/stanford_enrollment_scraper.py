#!/usr/bin/env python3
"""
Stanford Scraper using ScraperAPI Service

This version uses ScraperAPI which handles:
- Automatic proxy rotation
- Browser rendering
- Captcha solving
- Retry logic

To use:
1. Sign up for free account at https://www.scraperapi.com (5000 free requests)
2. Get your API key
3. Set environment variable: export SCRAPER_API_KEY=your_key_here
4. Run the script
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from urllib.parse import urljoin, quote
import json
import logging
from datetime import datetime
import os
from pathlib import Path
import pickle

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class StanfordScraperAPI:
    """Stanford scraper using ScraperAPI service."""
    
    def __init__(self):
        self.api_key = os.environ.get('SCRAPER_API_KEY', '')
        if not self.api_key:
            logger.warning("No SCRAPER_API_KEY found. Sign up at https://www.scraperapi.com")
            logger.info("Using direct requests instead (may be blocked)")
        
        self.base_url = "https://explorecourses.stanford.edu"
        self.scraper_api_url = "http://api.scraperapi.com"
        
        # Output directory
        self.output_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Checkpoint for resume
        self.checkpoint_file = Path(self.output_dir) / 'scraper_checkpoint.pkl'
        
        # Data storage
        self.courses_data = []
        self.stats = {'total_courses': 0, 'departments_processed': 0, 'errors': 0}
    
    def get_page(self, url, retries=3):
        """Fetch page using ScraperAPI or direct request."""
        if self.api_key:
            # Use ScraperAPI
            params = {
                'api_key': self.api_key,
                'url': url,
                'render': 'false',  # Disable JS rendering for speed (enrollment is in HTML)
                'country_code': 'us'
            }
            
            for attempt in range(retries):
                try:
                    response = requests.get(self.scraper_api_url, params=params, timeout=60)
                    if response.status_code == 200:
                        return response.text
                    elif response.status_code == 429:
                        logger.warning("Rate limit reached, waiting 10 seconds...")
                        time.sleep(10)  # Keep this - it's ScraperAPI's rate limit
                    else:
                        logger.error(f"ScraperAPI error: {response.status_code}")
                except Exception as e:
                    logger.error(f"Error fetching {url}: {e}")
                    # No delay - let ScraperAPI handle retries
        else:
            # Direct request (fallback)
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
    
    def get_academic_years(self):
        """Get available academic years."""
        logger.info("Getting academic years...")
        
        html = self.get_page(self.base_url)
        if not html:
            # Fallback to known years
            return [
                {'code': '20212022', 'name': '2021-2022'},
                {'code': '20222023', 'name': '2022-2023'},
                {'code': '20232024', 'name': '2023-2024'},
                {'code': '20242025', 'name': '2024-2025'},
            ]
        
        soup = BeautifulSoup(html, 'html.parser')
        years = []
        
        year_table = soup.find('table', id='years')
        if year_table:
            for link in year_table.find_all('a', href=True):
                year_name = link.get_text(strip=True)
                match = re.search(r'academicYear=(\d{8})', link['href'])
                if match:
                    years.append({
                        'code': match.group(1),
                        'name': year_name
                    })
        
        logger.info(f"Found {len(years)} years")
        return years or [{'code': '20242025', 'name': '2024-2025'}]
    
    def get_departments(self, year_code):
        """Get all departments for an academic year."""
        url = f"{self.base_url}/browse?academicYear={year_code}"
        logger.info(f"Getting departments from {url}")
        
        html = self.get_page(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        departments = []
        
        for container in soup.find_all('div', class_='departmentsContainer'):
            for school_header in container.find_all('h2', class_='schoolName'):
                school_name = school_header.get_text(strip=True)
                
                next_elem = school_header.find_next_sibling()
                while next_elem and next_elem.name == 'ul':
                    for link in next_elem.find_all('a'):
                        dept_text = link.get_text(strip=True)
                        match = re.match(r'(.+?)\s*\(([A-Z]+)\)', dept_text)
                        if match:
                            departments.append({
                                'name': match.group(1).strip(),
                                'code': match.group(2),
                                'school': school_name
                            })
                    next_elem = next_elem.find_next_sibling()
        
        logger.info(f"Found {len(departments)} departments")
        return departments
    
    def extract_enrollment_data(self, course_section):
        """Extract enrollment information from course section HTML."""
        # Get the parent container that has all course info
        container = course_section.parent if course_section.parent else course_section
        container_text = container.get_text()
        
        # FIRST: Try to find paired enrollment/capacity patterns
        paired_enrollment_patterns = [
            r'Students enrolled:\s*(\d+)\s*/\s*(\d+)',
            r'enrolled:\s*(\d+)\s*/\s*(\d+)',
            r'(\d+)\s*/\s*(\d+)\s*students',
            r'Enrollment:\s*(\d+)\s*/\s*(\d+)',
            r'(\d+)\s*enrolled.*?(\d+)\s*capacity',
            r'Current enrollment:\s*(\d+).*?Max enrollment:\s*(\d+)',
            r'Enrolled:\s*(\d+).*?Capacity:\s*(\d+)',
            # Simple pattern for "11 / 20" format that appears in schedule sections
            r'Schedule.*?(\d+)\s*/\s*(\d+)',
            r'Section.*?(\d+)\s*/\s*(\d+)'
        ]
        
        for pattern in paired_enrollment_patterns:
            match = re.search(pattern, container_text, re.IGNORECASE)
            if match:
                enrolled = match.group(1)
                capacity = match.group(2)
                logger.debug(f"Found paired enrollment: {enrolled}/{capacity}")
                return f"{enrolled}/{capacity}"
        
        # SECOND: Try to find single enrollment numbers (no capacity)
        single_enrollment_patterns = [
            r'Students enrolled:\s*(\d+)(?!\s*/)',  # "Students enrolled: 9" but not "9 /"
            r'Enrolled:\s*(\d+)(?!\s*/)',           # "Enrolled: 9"
            r'Current enrollment:\s*(\d+)(?!\s*/)', # "Current enrollment: 9"
            r'(\d+)\s+students?\s+enrolled',        # "9 students enrolled" or "1 student enrolled"
            r'Enrollment:\s*(\d+)(?!\s*/)',         # "Enrollment: 9"
            r'Class size:\s*(\d+)',                 # "Class size: 9"
            r'Total enrolled:\s*(\d+)',             # "Total enrolled: 9"
        ]
        
        for pattern in single_enrollment_patterns:
            match = re.search(pattern, container_text, re.IGNORECASE)
            if match:
                enrolled = match.group(1)
                logger.debug(f"Found single enrollment: {enrolled}")
                return enrolled  # Return just the enrollment number
        
        return None
    
    def extract_course_details(self, section_html, course_code, course_name):
        """Extract detailed course information including enrollment."""
        container = section_html.parent if section_html.parent else section_html
        container_text = container.get_text()
        
        # Extract enrollment
        enrollment = self.extract_enrollment_data(section_html)
        
        # Extract units
        units_match = re.search(r'(\d+)\s*units?', container_text, re.IGNORECASE)
        units = units_match.group(1) if units_match else None
        
        # Extract instructor
        instructor_match = re.search(r'Instructor[s]?:\s*([^.\n]+)', container_text, re.IGNORECASE)
        instructor = instructor_match.group(1).strip() if instructor_match else None
        
        # Extract schedule
        schedule_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4}\s*-\s*\d{1,2}/\d{1,2}/\d{4})', container_text)
        schedule = schedule_match.group(1) if schedule_match else None
        
        # Extract class number
        class_match = re.search(r'Class #\s*(\d+)', container_text)
        class_number = class_match.group(1) if class_match else None
        
        # Extract term/quarter (Autumn, Winter, Spring, Summer)
        term = None
        term_patterns = [
            r'Session:\s*\d{4}-\d{4}\s+(Autumn|Winter|Spring|Summer)',
            r'(Autumn|Winter|Spring|Summer)\s+\d{4}',
            r'\b(Aut|Win|Spr|Sum)\s+\d{4}',
            r'Terms?:\s*(Autumn|Winter|Spring|Summer|Aut|Win|Spr|Sum)',
        ]
        for pattern in term_patterns:
            term_match = re.search(pattern, container_text, re.IGNORECASE)
            if term_match:
                term_found = term_match.group(1)
                # Normalize abbreviations
                term_map = {'Aut': 'Autumn', 'Win': 'Winter', 'Spr': 'Spring', 'Sum': 'Summer'}
                term = term_map.get(term_found, term_found).title()
                break
        
        # If no term found, try to infer from schedule dates
        if not term and schedule:
            # Parse month from schedule to infer term
            month_match = re.search(r'^(\d{2})/', schedule)
            if month_match:
                month = int(month_match.group(1))
                if month in [9, 10, 11, 12]:
                    term = 'Autumn'
                elif month in [1, 2, 3]:
                    term = 'Winter'
                elif month in [4, 5]:
                    term = 'Spring'
                elif month in [6, 7, 8]:
                    term = 'Summer'
        
        return {
            'course_code': course_code,
            'course_name': course_name,
            'enrollment': enrollment,
            'units': units,
            'instructor': instructor,
            'schedule': schedule,
            'class_number': class_number,
            'term': term
        }
    
    def get_courses(self, dept_code, year_code):
        """Get all courses for a department with enrollment data."""
        courses = []
        page = 0
        
        while page < 20:  # Max 20 pages per department
            url = f"{self.base_url}/search?view=catalog&academicYear={year_code}"
            url += f"&page={page}&q={dept_code}&filter-coursestatus-Active=on"
            url += f"&filter-departmentcode-{dept_code}=on"
            
            html = self.get_page(url)
            if not html:
                break
            
            soup = BeautifulSoup(html, 'html.parser')
            page_courses = 0
            
            # Find all course sections
            page_courses_list = []  # Track courses from this page only
            for section in soup.find_all('h2'):
                text = section.get_text(strip=True)
                match = re.match(r'([A-Z]+\s+\d+[A-Z]*):\s*(.+)', text)
                if match:
                    course_code = match.group(1)
                    course_name = match.group(2)
                    
                    # Extract detailed course information including enrollment
                    course_details = self.extract_course_details(section, course_code, course_name)
                    courses.append(course_details)
                    page_courses_list.append(course_details)
                    page_courses += 1
            
            if page_courses == 0:
                break
            
            # Log with enrollment info (for this page only)
            page_enrollment_count = sum(1 for c in page_courses_list if c.get('enrollment'))
            logger.info(f"  Page {page}: Found {page_courses} courses ({page_enrollment_count} with enrollment)")
            page += 1
            
            # No delay needed - ScraperAPI handles rate limiting
            # time.sleep(1)
        
        return courses
    
    def save_checkpoint(self, year_idx, dept_idx):
        """Save progress checkpoint."""
        checkpoint = {
            'year_idx': year_idx,
            'dept_idx': dept_idx,
            'courses_data': self.courses_data,
            'stats': self.stats
        }
        with open(self.checkpoint_file, 'wb') as f:
            pickle.dump(checkpoint, f)
    
    def load_checkpoint(self):
        """Load saved checkpoint."""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'rb') as f:
                    return pickle.load(f)
            except:
                pass
        return None
    
    def scrape_all(self, test_mode=False):
        """Main scraping function."""
        logger.info("Starting Stanford scraping with ScraperAPI...")
        
        # Load checkpoint
        checkpoint = self.load_checkpoint()
        start_year = 0
        start_dept = 0
        if checkpoint:
            start_year = checkpoint.get('year_idx', 0)
            start_dept = checkpoint.get('dept_idx', 0)
            self.courses_data = checkpoint.get('courses_data', [])
            self.stats = checkpoint.get('stats', self.stats)
            logger.info(f"Resuming from checkpoint: year {start_year}, dept {start_dept}")
        
        # Get years
        years = self.get_academic_years()
        if test_mode:
            years = years[-1:]  # Only latest year for testing
        
        # Process each year
        for y_idx, year in enumerate(years[start_year:], start_year):
            logger.info(f"Processing {year['name']}")
            
            # Get departments
            departments = self.get_departments(year['code'])
            if test_mode:
                departments = departments[:3]  # Only 3 departments for testing
            
            # Resume from correct department
            dept_start = start_dept if y_idx == start_year else 0
            
            # Process each department
            for d_idx, dept in enumerate(departments[dept_start:], dept_start):
                logger.info(f"Processing {dept['name']} ({dept['code']})")
                
                try:
                    # Get courses
                    courses = self.get_courses(dept['code'], year['code'])
                    
                    # Add metadata
                    for course in courses:
                        course.update({
                            'academic_year': year['name'],
                            'department': dept['name'],
                            'school': dept['school'],
                            'scraped_at': datetime.now().isoformat()
                        })
                        # Term is already extracted in extract_course_details
                    
                    self.courses_data.extend(courses)
                    self.stats['total_courses'] += len(courses)
                    self.stats['departments_processed'] += 1
                    
                    logger.info(f"  Found {len(courses)} courses")
                    
                    # Save checkpoint
                    self.save_checkpoint(y_idx, d_idx + 1)
                    
                    # No delay - ScraperAPI handles all rate limiting
                    
                except Exception as e:
                    logger.error(f"Error processing {dept['name']}: {e}")
                    self.stats['errors'] += 1
            
            # Reset department counter for next year
            start_dept = 0
        
        # Clear checkpoint on completion
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
        
        logger.info(f"Scraping complete! Total courses: {self.stats['total_courses']}")
        return self.courses_data
    
    def save_results(self):
        """Save results to CSV and JSON."""
        if not self.courses_data:
            logger.warning("No data to save")
            return
        
        # Save CSV
        df = pd.DataFrame(self.courses_data)
        csv_file = Path(self.output_dir) / 'stanford_enrollment.csv'
        df.to_csv(csv_file, index=False)
        logger.info(f"Saved {len(df)} courses to {csv_file}")
        
        # Save JSON
        json_file = Path(self.output_dir) / 'stanford_enrollment.json'
        with open(json_file, 'w') as f:
            json.dump(self.courses_data, f, indent=2)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"Total courses: {self.stats['total_courses']}")
        print(f"Departments processed: {self.stats['departments_processed']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"{'='*60}")

def main():
    """Main entry point."""
    scraper = StanfordScraperAPI()
    
    # Check for API key
    if not scraper.api_key:
        print("\n" + "="*60)
        print("SETUP REQUIRED")
        print("="*60)
        print("1. Sign up for free at: https://www.scraperapi.com")
        print("2. Get your API key (5000 free requests)")
        print("3. Set environment variable:")
        print("   export SCRAPER_API_KEY=your_key_here")
        print("4. Run this script again")
        print("="*60)
        print("\nProceed without API key? (y/n): ", end="")
        
        response = input().strip().lower()
        if response != 'y':
            return
    
    # Run in test mode if specified
    test_mode = os.environ.get('TEST_MODE', '').lower() in ('1', 'true', 'yes')
    
    # Run scraper
    scraper.scrape_all(test_mode=test_mode)
    
    # Save results
    scraper.save_results()

if __name__ == "__main__":
    main()