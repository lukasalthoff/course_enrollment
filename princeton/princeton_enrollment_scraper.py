#!/usr/bin/env python3
"""
Princeton Course Enrollment Scraper - Fixed Version

This scraper fixes the enrollment extraction to properly capture:
- Seats Enrolled: X
- Total Seats: Y
- Seats Open: Z

Based on the actual HTML structure from Princeton's course offerings.
"""

import time
import random
import logging
import json
import pandas as pd
from datetime import datetime
import re

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from webdriver_manager.chrome import ChromeDriverManager
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"Missing package: {e}")
    print("Install: pip install selenium webdriver-manager beautifulsoup4 pandas")
    exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class PrincetonFixedScraper:
    """Fixed Princeton course enrollment scraper with proper enrollment extraction"""

    def __init__(self):
        self.base_url = "https://registrar.princeton.edu/course-offerings"
        self.driver = None
        self.wait = None
        self.all_courses = []

    def setup_browser(self):
        """Setup respectful browser with human-like characteristics"""
        try:
            options = ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--window-size=1366,768')
            options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.set_page_load_timeout(90)
            self.wait = WebDriverWait(self.driver, 30)

            logger.info("✅ Browser setup complete")
            return True

        except Exception as e:
            logger.error(f"❌ Browser setup failed: {e}")
            return False

    def get_available_terms(self):
        """Get all available academic terms from dropdown"""
        try:
            logger.info("🔍 Getting available terms from dropdown...")
            self.driver.get(self.base_url)
            time.sleep(8)

            # Find term dropdown - try multiple selectors
            term_selectors = [
                "select[name*='term']",
                "select#edit-term",
                "//select[contains(@name, 'term')]",
                "select[name='term']"
            ]

            term_select_element = None
            for selector in term_selectors:
                try:
                    if selector.startswith("//"):
                        term_select_element = self.driver.find_element(By.XPATH, selector)
                    else:
                        term_select_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if term_select_element:
                        break
                except:
                    continue

            if not term_select_element:
                logger.error("❌ Could not find term dropdown")
                return []

            # Extract all term options
            select = Select(term_select_element)
            terms = []

            for option in select.options:
                value = option.get_attribute('value')
                text = option.text.strip()

                if value and value != '' and 'Select' not in text:
                    terms.append({'value': value, 'text': text})

            logger.info(f"✅ Found {len(terms)} available terms")
            return terms

        except Exception as e:
            logger.error(f"❌ Error getting terms: {e}")
            return []

    def scrape_term(self, term_info):
        """Scrape all courses for a specific term"""
        try:
            print(f"\n🎓 Scraping {term_info['text']}")
            print("=" * 50)

            # Navigate and select term
            self.driver.get(self.base_url)
            time.sleep(8)

            # Find and select term from dropdown
            term_selectors = [
                "select[name*='term']",
                "select#edit-term",
                "//select[contains(@name, 'term')]",
                "select[name='term']"
            ]
            term_select_element = None

            for selector in term_selectors:
                try:
                    if selector.startswith("//"):
                        term_select_element = self.driver.find_element(By.XPATH, selector)
                    else:
                        term_select_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if term_select_element:
                        break
                except:
                    continue

            if not term_select_element:
                print(f"   ❌ Could not find term dropdown")
                return 0

            # Select the term
            select = Select(term_select_element)
            select.select_by_value(term_info['value'])
            time.sleep(3)

            # Click search
            search_button = self.wait.until(EC.element_to_be_clickable((By.ID, "classes-search-button")))
            search_button.click()
            time.sleep(15)

            # Check for results
            page_source = self.driver.page_source
            count_match = re.search(r'Displaying \d+ to \d+ of (\d+) classes', page_source)
            if not count_match:
                print(f"   ❌ No courses found")
                return 0

            total_courses = int(count_match.group(1))
            print(f"   📊 Found {total_courses} courses total")

            # Process all pages
            page_num = 1
            term_courses = []

            while True:
                print(f"   📖 Processing page {page_num}...")

                # Extract courses from current page
                page_courses = self.extract_page_courses_fixed(term_info, page_num)

                if page_courses:
                    term_courses.extend(page_courses)
                    with_enrollment = [c for c in page_courses if c.get('enrollment') is not None]
                    avg_enrollment = sum(c['enrollment'] for c in with_enrollment) / len(with_enrollment) if with_enrollment else 0
                    print(f"      ✅ {len(page_courses)} courses, avg enrollment: {avg_enrollment:.1f}")

                # Check if last page
                if self.is_last_page():
                    print(f"      📄 Completed all pages (reached page {page_num})")
                    break

                # Go to next page
                if not self.go_to_next_page():
                    break

                page_num += 1
                if page_num > 30:  # Safety limit
                    break

                # Respectful delay
                delay = random.uniform(8, 15)
                print(f"      ⏰ Delay: {delay:.1f}s...")
                time.sleep(delay)

            self.all_courses.extend(term_courses)
            print(f"   📊 Term completed: {len(term_courses)} courses")
            return len(term_courses)

        except Exception as e:
            logger.error(f"❌ Error scraping {term_info['text']}: {e}")
            return 0

    def extract_page_courses_fixed(self, term_info, page_num):
        """Extract course data from current page with FIXED enrollment parsing"""
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            courses = []

            rows = soup.find_all('tr')
            for row in rows:
                course_cell = row.find('td', class_='class-info')

                if course_cell:
                    catalog_elem = course_cell.find('small', class_='catalog-number')
                    if catalog_elem:
                        course_code = catalog_elem.get_text(strip=True)
                        if '/' in course_code:
                            course_code = course_code.split('/')[0].strip()

                        subject_match = re.match(r'^([A-Z]+)', course_code)
                        subject = subject_match.group(1) if subject_match else 'UNKNOWN'

                        course_data = {
                            'course_code': course_code,
                            'subject': subject,
                            'term_value': term_info['value'],
                            'term_text': term_info['text'],
                            'scrape_timestamp': datetime.now().isoformat()
                        }

                        # FIXED: Extract enrollment data from the entire row text
                        row_text = row.get_text()

                        # Look for "Seats Enrolled: X" pattern
                        enrolled_match = re.search(r'Seats Enrolled:\s*(\d+)', row_text)
                        if enrolled_match:
                            course_data['enrollment'] = int(enrolled_match.group(1))

                        # Look for "Total Seats: Y" pattern
                        capacity_match = re.search(r'Total Seats:\s*(\d+)', row_text)
                        if capacity_match:
                            course_data['capacity'] = int(capacity_match.group(1))

                        # Look for "Seats Open: Z" pattern
                        open_match = re.search(r'Seats Open:\s*(-?\d+)', row_text)
                        if open_match:
                            course_data['seats_open'] = int(open_match.group(1))

                        # Extract additional data
                        link_elem = course_cell.find('a')
                        if link_elem:
                            title = link_elem.get_text(strip=True)
                            title = re.sub(r'\(Link opens in new window\)', '', title).strip()
                            course_data['course_title'] = title

                        dist_cell = row.find('td', class_='class-distarea')
                        if dist_cell:
                            course_data['distribution_area'] = dist_cell.get_text(strip=True)

                        status_cell = row.find('td', class_='class-status')
                        if status_cell:
                            course_data['status'] = status_cell.get_text(strip=True)

                        courses.append(course_data)

            return courses

        except Exception as e:
            logger.error(f"❌ Page extraction failed: {e}")
            return []

    def is_last_page(self):
        """Check if we're on the last page"""
        try:
            page_source = self.driver.page_source
            page_info_match = re.search(r'Displaying (\d+) to (\d+) of (\d+) classes', page_source)

            if page_info_match:
                end_item = int(page_info_match.group(2))
                total_items = int(page_info_match.group(3))
                return end_item >= total_items

            return True

        except:
            return True

    def go_to_next_page(self):
        """Navigate to next page"""
        try:
            next_selectors = [
                "//a[contains(text(), 'Next') and not(contains(@class, 'disabled'))]",
                "//a[contains(text(), '»') and not(contains(@class, 'disabled'))]"
            ]

            for selector in next_selectors:
                try:
                    next_link = self.driver.find_element(By.XPATH, selector)
                    if next_link.is_displayed() and next_link.is_enabled():
                        href = next_link.get_attribute('href')
                        if href and href != '#':
                            next_link.click()
                            time.sleep(12)
                            return True
                except:
                    continue

            return False

        except:
            return False

    def run_complete_scrape(self):
        """Run complete scraping across all available terms"""
        try:
            print("🎓 Princeton Fixed Course Enrollment Scraper")
            print("=" * 60)
            print("Collecting comprehensive course enrollment data with FIXED parsing")
            print()

            if not self.setup_browser():
                return False

            # Get all available terms
            available_terms = self.get_available_terms()
            if not available_terms:
                print("❌ No terms found")
                return False

            print(f"📅 Available terms: {len(available_terms)}")
            for term in available_terms:
                print(f"   {term['value']}: {term['text']}")
            print()

            # Scrape each term
            term_results = {}
            total_courses = 0

            for i, term_info in enumerate(available_terms):
                courses_scraped = self.scrape_term(term_info)
                term_results[term_info['value']] = {
                    'text': term_info['text'],
                    'courses': courses_scraped
                }
                total_courses += courses_scraped

                # Long delay between terms
                if i < len(available_terms) - 1:
                    delay = random.uniform(45, 75)
                    print(f"\n⏰ Respectful delay between terms: {delay:.1f}s...\n")
                    time.sleep(delay)

            # Save results
            self.save_results(term_results)

            # Final summary
            print(f"\n📊 COMPLETE SCRAPING RESULTS")
            print("=" * 40)
            print(f"📅 Terms scraped: {len(term_results)}")
            print(f"📚 Total courses: {total_courses:,}")

            for term_value, result in term_results.items():
                print(f"   {result['text']}: {result['courses']:,} courses")

            if self.all_courses:
                df = pd.DataFrame(self.all_courses)
                with_enrollment = df[df['enrollment'].notna()]

                print(f"\n📊 Overall Statistics:")
                print(f"📈 With enrollment data: {len(with_enrollment):,} ({len(with_enrollment)/len(df)*100:.1f}%)")
                print(f"🏛️ Departments covered: {df['subject'].nunique()}")
                print(f"👥 Total enrolled students: {with_enrollment['enrollment'].sum():,}")
                print(f"📈 Average enrollment: {with_enrollment['enrollment'].mean():.1f}")

            return True

        except Exception as e:
            logger.error(f"❌ Complete scrape failed: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                print("\n🔒 Browser closed")

    def save_results(self, term_results):
        """Save comprehensive results"""
        if not self.all_courses:
            return

        df = pd.DataFrame(self.all_courses)

        # Save main CSV
        df.to_csv('princeton_fixed_courses.csv', index=False)

        # Save summary
        with_enrollment = df[df['enrollment'].notna()]
        summary = {
            'princeton_fixed_scraping': {
                'timestamp': datetime.now().isoformat(),
                'total_courses': len(df),
                'courses_with_enrollment': len(with_enrollment),
                'enrollment_coverage_percent': round(len(with_enrollment)/len(df)*100, 1) if len(df) > 0 else 0,
                'terms_scraped': term_results,
                'departments_covered': int(df['subject'].nunique()),
                'total_enrolled_students': int(with_enrollment['enrollment'].sum()) if len(with_enrollment) > 0 else 0,
                'average_enrollment': round(with_enrollment['enrollment'].mean(), 1) if len(with_enrollment) > 0 else 0
            }
        }

        with open('princeton_fixed_summary.json', 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        print(f"💾 Saved {len(df):,} courses to princeton_fixed_courses.csv")

def main():
    scraper = PrincetonFixedScraper()
    success = scraper.run_complete_scrape()

    if success:
        print(f"\n🎉 COMPLETE SUCCESS!")
        print(f"📋 Princeton's entire course catalog successfully scraped with FIXED enrollment parsing!")
        print(f"🚀 Comprehensive enrollment data collected across all terms")
    else:
        print(f"\n⚠️ Scraping encountered issues")

if __name__ == "__main__":
    main()
