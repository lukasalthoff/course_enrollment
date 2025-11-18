# University Course Enrollment Scrapers

Comprehensive collection of scrapers for university course enrollment data across multiple institutions.

---

## 📚 Universities Covered

### Existing Data (Already Scraped)
1. **Stanford University** - explorecourses.stanford.edu
2. **Princeton University** - registrar.princeton.edu
3. **Harvard University** - (CSV files 2013-2026)

### New Scrapers Implemented
4. **UC Berkeley** - berkeleytime.com (10+ years of data)
5. **UCLA** - hotseat.io (2+ years of data)
6. **University of Virginia** - louslist.org / hooslist.virginia.edu (6+ years)
7. **UW-Madison** - madgrades.com (18+ years, 2006-present!)
8. **UC San Diego** - cape.ucsd.edu (14 years, 2007-2021)

---

## 🚀 Quick Start

### Prerequisites

```bash
# Install required packages
pip install requests beautifulsoup4 pandas selenium webdriver-manager

# Optional: Sign up for ScraperAPI (5000 free requests)
# https://www.scraperapi.com
export SCRAPER_API_KEY=your_key_here
```

### Running Individual Scrapers

Each university has its own scraper in a dedicated directory:

```bash
# UC Berkeley
cd uc_berkeley
python berkeley_enrollment_scraper.py

# UCLA
cd ucla
python ucla_enrollment_scraper.py

# UVA
cd uva
python uva_enrollment_scraper.py

# UW-Madison
cd uw_madison
python madison_enrollment_scraper.py

# UC San Diego
cd uc_san_diego
python ucsd_enrollment_scraper.py
```

### Running All Scrapers

Use the master script to run multiple scrapers:

```bash
# Run all scrapers
python run_all_scrapers.py

# Run specific universities
python run_all_scrapers.py --universities berkeley,ucla,uva

# Run in test mode (limited scraping)
python run_all_scrapers.py --test-mode

# Skip universities with existing data
python run_all_scrapers.py --skip-existing

# List available universities
python run_all_scrapers.py --list
```

---

## 📊 Data Sources Details

### 1. UC Berkeley (BerkeleyTime)

**Website**: https://berkeleytime.com/
**Data Range**: 2014-present (10+ years)
**Data Type**: Course enrollment, historical trends, grade distributions
**API**: Berkeley Student Information System APIs

**Features**:
- Real-time enrollment tracking
- Historical enrollment comparisons
- Grade distribution data
- Course reviews

**Scraper**: `uc_berkeley/berkeley_enrollment_scraper.py`

**Output**:
- `berkeley_enrollment.csv`
- `berkeley_enrollment.json`

---

### 2. UCLA (Hotseat)

**Website**: https://hotseat.io/
**Data Range**: 2021-present (2+ years)
**Data Type**: Enrollment trends, grade distributions, professor reviews
**API**: UCLA Registrar data integration

**Features**:
- Enrollment progress tracking
- Class fill-up predictions
- Grade distributions
- Professor ratings
- Textbook information

**Scraper**: `ucla/ucla_enrollment_scraper.py`

**Output**:
- `ucla_enrollment.csv`
- `ucla_enrollment.json`

---

### 3. University of Virginia (Lou's List / Hoos' List)

**Website**: https://louslist.org/ OR https://hooslist.virginia.edu/
**Data Range**: 2018-present (6+ years)
**Data Type**: Course schedules, enrollment, waitlist, capacity
**Source**: UVA Student Information System (SIS)

**Features**:
- Historical enrollment data
- Waitlist information
- Capacity tracking
- Section details

**Scraper**: `uva/uva_enrollment_scraper.py`

**Options**:
```python
# Use Lou's List (legacy)
scraper = UVAEnrollmentScraperAPI(use_hooslist=False)

# Use Hoos' List (official)
scraper = UVAEnrollmentScraperAPI(use_hooslist=True)
```

**Output**:
- `uva_enrollment.csv`
- `uva_enrollment.json`

---

### 4. UW-Madison (Madgrades)

**Website**: https://madgrades.com/
**Data Range**: 2006-present (18+ years!)
**Data Type**: Grade distributions, enrollment, instructor data
**Additional**: Available on Kaggle and GitHub

**Features**:
- Exceptional historical depth
- Grade distribution analysis
- Instructor information
- Course-level statistics

**Alternative Data Sources**:
- **Kaggle**: https://www.kaggle.com/datasets/Madgrades/uw-madison-courses
- **GitHub**: https://github.com/Madgrades/madgrades-data
- **Official**: https://registrar.wisc.edu/grade-reports/

**Scraper**: `uw_madison/madison_enrollment_scraper.py`

**Recommendation**: For 2006-2017 data, downloading the Kaggle dataset is easier than scraping.

**Output**:
- `madison_enrollment.csv`
- `madison_enrollment.json`

---

### 5. UC San Diego (CAPE)

**Website**: https://cape.ucsd.edu/
**Data Range**: 2007-2021 (14 years)
**Data Type**: Course evaluations with enrollment context
**Source**: CAPE (Course And Professor Evaluations)

**Features**:
- Course evaluation statistics
- Enrollment numbers
- GPA averages
- Professor recommendations
- Student evaluation counts

**Scraper**: `uc_san_diego/ucsd_enrollment_scraper.py`

**Output**:
- `ucsd_enrollment.csv`
- `ucsd_enrollment.json`

---

## 🔧 Scraper Architecture

### Common Features

All scrapers follow a consistent architecture:

1. **ScraperAPI Integration**: Optional use of ScraperAPI for better reliability
2. **Rate Limiting**: Respectful delays between requests
3. **Error Handling**: Comprehensive logging and error recovery
4. **Data Export**: CSV and JSON formats
5. **Progress Tracking**: Real-time logging of scraping progress

### Class Structure

```python
class UniversityScraperAPI:
    def __init__(self):
        # Initialize with ScraperAPI key

    def get_page(self, url):
        # Fetch page using ScraperAPI or direct requests

    def scrape_all(self):
        # Main scraping logic

    def save_results(self):
        # Export to CSV and JSON
```

---

## 🔑 Using ScraperAPI

ScraperAPI is optional but recommended for:
- Avoiding IP blocks
- Handling CAPTCHAs
- Automatic proxy rotation
- Better reliability

### Setup

```bash
# 1. Sign up at https://www.scraperapi.com (5000 free requests)

# 2. Get your API key

# 3. Set environment variable
export SCRAPER_API_KEY=your_key_here

# 4. Run scraper (will automatically use ScraperAPI)
python berkeley_enrollment_scraper.py
```

### Without ScraperAPI

Scrapers will automatically fall back to direct requests if no API key is set.

---

## 📁 Output Format

### CSV Format

All scrapers export consistent CSV files with columns like:

```csv
course_code,course_name,enrollment,capacity,waitlist,semester,department,instructor,scraped_at
CS 61A,Structure and Interpretation,350,400,15,Fall 2024,Computer Science,DeNero,2025-11-18T...
```

### JSON Format

Detailed nested structure preserving all scraped data:

```json
[
  {
    "course_code": "CS 61A",
    "course_name": "Structure and Interpretation",
    "enrollment": 350,
    "capacity": 400,
    "waitlist": 15,
    "semester": "Fall 2024",
    "department": "Computer Science",
    "instructor": "DeNero",
    "scraped_at": "2025-11-18T..."
  }
]
```

---

## ⚙️ Configuration Options

### Test Mode

Run scrapers in limited mode for testing:

```python
# Individual scraper
scraper.scrape_all(max_semesters=4)  # Limit semesters
scraper.scrape_all(max_departments=3)  # Limit departments

# Master scraper
python run_all_scrapers.py --test-mode
```

### Selecting Specific Terms

```python
# UC Berkeley - specific semesters
scraper.scrape_all(semesters=['2024-fall', '2024-spring'])

# UVA - specific semester codes
scraper.scrape_semester('1248', 'Fall 2024')

# UCSD - specific departments
scraper.scrape_all(departments=['CSE', 'MATH'])
```

---

## 🔍 Troubleshooting

### Common Issues

#### 1. Rate Limiting

**Problem**: Getting 429 errors or blocked
**Solution**:
- Use ScraperAPI
- Increase delays between requests
- Run in test mode first

#### 2. HTML Structure Changes

**Problem**: Scraper returns no data
**Solution**:
- Check if website HTML has changed
- Update parsing logic
- Enable debug logging

#### 3. Authentication Required

**Problem**: Some data requires login
**Solution**:
- Some universities restrict data access
- Check UNIVERSITY_WEBSITES_RESEARCH.md for alternatives
- Consider using official APIs if available

### Debugging

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check log files:
```bash
cat berkeley_scraper.log
cat ucla_scraper.log
# etc.
```

---

## 📖 Additional Resources

### Research Document

See `UNIVERSITY_WEBSITES_RESEARCH.md` for:
- Detailed research on 27+ universities
- Verification of data availability
- Legal and ethical considerations
- Additional universities to consider

### Data Analysis

Example analysis workflows:

```python
import pandas as pd

# Load data
berkeley = pd.read_csv('uc_berkeley/berkeley_enrollment.csv')
ucla = pd.read_csv('ucla/ucla_enrollment.csv')

# Combine datasets
all_data = pd.concat([berkeley, ucla])

# Analyze trends
enrollment_by_semester = all_data.groupby('semester')['enrollment'].mean()
```

---

## ⚖️ Legal & Ethical Considerations

### Terms of Service

- Review ToS for each website before scraping
- Respect robots.txt directives
- Some sites explicitly allow educational data access

### Rate Limiting

- Implement respectful delays (2-5 seconds between requests)
- Avoid overwhelming servers
- Use ScraperAPI for better distribution

### Data Attribution

- Credit original data sources
- These are public educational resources
- Use responsibly for research/educational purposes

### Privacy

- Do not scrape personal information
- Aggregate enrollment numbers are public
- Individual student data is protected by FERPA

---

## 🤝 Contributing

### Adding New Universities

1. Research data availability (see UNIVERSITY_WEBSITES_RESEARCH.md)
2. Create new directory: `university_name/`
3. Implement scraper following existing patterns
4. Add to `run_all_scrapers.py` configuration
5. Update this README

### Improving Existing Scrapers

1. Test scraper to identify issues
2. Update parsing logic for HTML changes
3. Enhance error handling
4. Submit pull request with changes

---

## 📝 License

These scrapers are provided for educational and research purposes. Respect the terms of service of each data source.

---

## 🎯 Summary

| University | Scraper | Data Range | Best For |
|-----------|---------|------------|----------|
| UC Berkeley | ✅ | 2014-present (10+ yrs) | Historical trends |
| UW-Madison | ✅ | 2006-present (18+ yrs) | Longest history |
| UVA | ✅ | 2018-present (6+ yrs) | Waitlist data |
| UCLA | ✅ | 2021-present (2+ yrs) | Recent data |
| UCSD | ✅ | 2007-2021 (14 yrs) | Evaluations |
| Stanford | ✅ | Multiple years | Existing |
| Princeton | ✅ | Multiple years | Existing |
| Harvard | ✅ | 2013-2026 | Existing |

**Total**: 8 universities, 100+ years of combined enrollment data!

---

**Last Updated**: 2025-11-18
**Maintainer**: Course Enrollment Research Project
