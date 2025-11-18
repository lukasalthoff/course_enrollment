#!/usr/bin/env python3
"""
Master Script to Run All University Enrollment Scrapers

This script coordinates running all university scrapers and consolidates results.

Universities included:
1. Stanford - explorecourses.stanford.edu
2. Princeton - registrar.princeton.edu/course-offerings
3. Harvard - (data files already collected)
4. UC Berkeley - berkeleytime.com
5. UCLA - hotseat.io
6. UVA - louslist.org / hooslist.virginia.edu
7. UW-Madison - madgrades.com
8. UC San Diego - cape.ucsd.edu

Usage:
    python run_all_scrapers.py [options]

Options:
    --universities NAMES    Comma-separated list of universities to scrape
    --test-mode            Run in test mode (limited scraping)
    --skip-existing        Skip universities with existing data files
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from pathlib import Path
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('all_scrapers.log', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MasterScraper:
    """Coordinates running all university scrapers."""

    def __init__(self, test_mode=False):
        self.test_mode = test_mode
        self.base_dir = Path(__file__).parent

        # University configurations
        self.universities = {
            'stanford': {
                'name': 'Stanford University',
                'directory': 'stanford',
                'scraper': 'stanford_enrollment_scraper.py',
                'data_files': ['stanford_enrollment.csv', 'stanford_enrollment.json']
            },
            'princeton': {
                'name': 'Princeton University',
                'directory': 'princeton',
                'scraper': 'princeton_enrollment_scraper.py',
                'data_files': ['princeton_enrollment.csv', 'princeton_enrollment.json']
            },
            'berkeley': {
                'name': 'UC Berkeley',
                'directory': 'uc_berkeley',
                'scraper': 'berkeley_enrollment_scraper.py',
                'data_files': ['berkeley_enrollment.csv', 'berkeley_enrollment.json']
            },
            'ucla': {
                'name': 'UCLA',
                'directory': 'ucla',
                'scraper': 'ucla_enrollment_scraper.py',
                'data_files': ['ucla_enrollment.csv', 'ucla_enrollment.json']
            },
            'uva': {
                'name': 'University of Virginia',
                'directory': 'uva',
                'scraper': 'uva_enrollment_scraper.py',
                'data_files': ['uva_enrollment.csv', 'uva_enrollment.json']
            },
            'wisconsin': {
                'name': 'UW-Madison',
                'directory': 'uw_madison',
                'scraper': 'madison_enrollment_scraper.py',
                'data_files': ['madison_enrollment.csv', 'madison_enrollment.json']
            },
            'ucsd': {
                'name': 'UC San Diego',
                'directory': 'uc_san_diego',
                'scraper': 'ucsd_enrollment_scraper.py',
                'data_files': ['ucsd_enrollment.csv', 'ucsd_enrollment.json']
            }
        }

        self.results = {}

    def check_existing_data(self, university_key):
        """Check if data files already exist for a university."""
        config = self.universities[university_key]
        uni_dir = self.base_dir / config['directory']

        for data_file in config['data_files']:
            file_path = uni_dir / data_file
            if file_path.exists():
                return True

        return False

    def run_scraper(self, university_key):
        """Run scraper for a specific university."""
        config = self.universities[university_key]
        logger.info(f"Running scraper for {config['name']}...")

        uni_dir = self.base_dir / config['directory']
        scraper_path = uni_dir / config['scraper']

        if not scraper_path.exists():
            logger.error(f"Scraper not found: {scraper_path}")
            return False

        # Change to university directory
        original_dir = os.getcwd()
        os.chdir(uni_dir)

        try:
            # Import and run the scraper module
            import importlib.util
            spec = importlib.util.spec_from_file_location("scraper", config['scraper'])
            scraper_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(scraper_module)

            # Run main function if available
            if hasattr(scraper_module, 'main'):
                scraper_module.main()
                logger.info(f"Completed scraping {config['name']}")
                return True
            else:
                logger.warning(f"No main() function found in {config['scraper']}")
                return False

        except Exception as e:
            logger.error(f"Error running scraper for {config['name']}: {e}")
            return False

        finally:
            # Return to original directory
            os.chdir(original_dir)

    def run_all(self, selected_universities=None, skip_existing=False):
        """
        Run all scrapers.

        Args:
            selected_universities: List of university keys to run. If None, runs all.
            skip_existing: Skip universities that already have data files.
        """
        print("\n" + "="*70)
        print("MASTER UNIVERSITY ENROLLMENT SCRAPER")
        print("="*70)
        print(f"Mode: {'TEST' if self.test_mode else 'PRODUCTION'}")
        print(f"Total universities configured: {len(self.universities)}")
        print("="*70 + "\n")

        universities_to_run = selected_universities or list(self.universities.keys())

        for uni_key in universities_to_run:
            if uni_key not in self.universities:
                logger.warning(f"Unknown university: {uni_key}")
                continue

            config = self.universities[uni_key]

            # Check if we should skip
            if skip_existing and self.check_existing_data(uni_key):
                logger.info(f"Skipping {config['name']} - data already exists")
                self.results[uni_key] = {'status': 'skipped', 'reason': 'existing_data'}
                continue

            # Run scraper
            print(f"\n{'='*70}")
            print(f"SCRAPING: {config['name']}")
            print(f"{'='*70}\n")

            success = self.run_scraper(uni_key)

            self.results[uni_key] = {
                'status': 'success' if success else 'failed',
                'timestamp': datetime.now().isoformat()
            }

        self.print_summary()
        self.save_results()

    def print_summary(self):
        """Print summary of scraping results."""
        print("\n" + "="*70)
        print("SCRAPING SUMMARY")
        print("="*70)

        for uni_key, result in self.results.items():
            config = self.universities[uni_key]
            status_symbol = "✅" if result['status'] == 'success' else "❌" if result['status'] == 'failed' else "⏭️ "
            print(f"{status_symbol} {config['name']:30} - {result['status']}")

        print("="*70)

        # Count results
        successful = sum(1 for r in self.results.values() if r['status'] == 'success')
        failed = sum(1 for r in self.results.values() if r['status'] == 'failed')
        skipped = sum(1 for r in self.results.values() if r['status'] == 'skipped')

        print(f"\nSuccessful: {successful}")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")
        print(f"Total: {len(self.results)}")

    def save_results(self):
        """Save scraping results summary."""
        results_file = self.base_dir / 'scraping_results.json'

        summary = {
            'timestamp': datetime.now().isoformat(),
            'test_mode': self.test_mode,
            'results': self.results
        }

        with open(results_file, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Results saved to {results_file}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run university enrollment scrapers'
    )

    parser.add_argument(
        '--universities',
        type=str,
        help='Comma-separated list of universities to scrape (stanford,berkeley,ucla,...)'
    )

    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='Run in test mode (limited scraping)'
    )

    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip universities with existing data files'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='List available universities and exit'
    )

    args = parser.parse_args()

    # Create master scraper
    master = MasterScraper(test_mode=args.test_mode)

    # List universities if requested
    if args.list:
        print("\nAvailable universities:")
        for key, config in master.universities.items():
            print(f"  {key:15} - {config['name']}")
        return

    # Parse selected universities
    selected = None
    if args.universities:
        selected = [u.strip() for u in args.universities.split(',')]

    # Run scrapers
    master.run_all(
        selected_universities=selected,
        skip_existing=args.skip_existing
    )

if __name__ == "__main__":
    main()
