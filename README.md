# University Course Enrollment Scrapers

This directory contains course enrollment scrapers and collected data for multiple universities.

## University Folders

### 🎓 Stanford University (`stanford/`)
- **Status**: ✅ Complete
- **Scraper**: `stanford_enrollment_scraper.py`
- **Data**: 1,483 total courses across 5 academic years (2020-2025)
- **Enrollment data**: 388 courses with enrollment information
- **Average enrollment**: 38.1 students
- **Average capacity**: 42.5 students
- **Website**: https://explorecourses.stanford.edu
- **Rate limiting**: ⚠️ **CRITICAL** - Stanford implements anti-scraping measures after sustained activity

### 🎓 Princeton University (`princeton/`)
- **Status**: ✅ Complete
- **Scraper**: `princeton_enrollment_scraper.py`
- **Data**: ~11,000+ courses across 7 academic terms (2021-2026)
- **Terms available**: Fall 2021-22 through Fall 2025-26
- **Enrollment coverage**: 99.9% of courses with complete enrollment data
- **Average enrollment**: ~15 students per course
- **Website**: https://registrar.princeton.edu/course-offerings
- **Key breakthrough**: Dropdown-based term selection (URL parameters don't work for different years)
- **Technical success**: Respectful scraping (45-75s delays) completely avoids anti-bot measures

### 🎓 Harvard University (`harvard/`)
- **Status**: ✅ Data Collected
- **Source**: https://registrar.fas.harvard.edu/links/archive/enrollment-reports?page=0
- **Data**: 24 files across 13 academic years (2013-2026)
- **Academic Years**: 2013-2014 through 2025-2026
- **Semesters**: Both Fall and Spring for most years
- **Format**: CSV files with enrollment data by course

## Common Features

All scrapers include:
- **Rate limiting** to respect university servers
- **Comprehensive data extraction** (enrollment, capacity, instructors, schedules, etc.)
- **Multiple academic years** support
- **Error handling** and retry mechanisms
- **Detailed logging** for debugging

## Data Fields (Standardized across universities)

- `course_code`: Department code + course number
- `course_name`: Full course title
- `academic_year`: Academic year (e.g., '2020-2021')
- `school`: School offering the course
- `department`: Department offering the course
- `enrollment`: Number of enrolled students
- `capacity`: Maximum enrollment capacity
- `units`: Course units/credits
- `instructor`: Course instructor(s)
- `schedule`: Class schedule
- `quarter/semester`: Academic term
- `class_number`: University class number
- `grading`: Grading policy
- `description`: Course description

## Technical Implementation Details

### Princeton-Specific Breakthrough
- **Critical discovery**: Academic terms MUST be selected via dropdown menu, not URL parameters
- **Term selection**: 7 available terms from Fall 2021-22 to Fall 2025-26
- **Dropdown interaction**: Uses Selenium Select() to choose from term options
- **Pagination**: Advanced detection prevents getting stuck on last page
- **Enrollment extraction**: Parses "Seats Enrolled: X" patterns from HTML tables
- **Respectful timing**: 8-15s between pages, 45-75s between terms
- **Success rate**: 99.9% enrollment data coverage across all terms
- **CloudFlare bypass**: Successfully navigated advanced anti-bot protection with human-like behavior
- **Term codes**: 4-digit codes (e.g., 1262=Fall 2025-26, 1254=Spring 2024-25)
- **Data structure**: Course code, title, enrollment, capacity, distribution requirements, status

### Stanford-Specific Patterns
- **Course extraction**: Parse h2 elements with pattern `"DEPARTMENT CODE: Course Name"`
- **Enrollment patterns**:
  - `"Students enrolled: X / Y"`
  - `"enrolled: X / Y"`
  - `"X / Y students"`
  - `"X enrolled / Y capacity"`
- **URL structure**: `/search?view=catalog&academicYear=YYYY&filter-departmentcode-DEPT=on`
- **Academic years**: Available via table with id='years'
- **Departments**: Organized by schools in containers with class='departmentsContainer'

### Rate Limiting Requirements
- **Princeton**: 45-75 second delays between terms, 8-15 seconds between pages
- **Stanford**: 5-12 second delays between requests, 8-15 seconds for retries
- **Anti-scraping measures**: Respectful timing prevents triggering protection
- **Success factor**: Human-like behavior patterns essential for data access

## Setup

### Quick Start (All Universities)
```bash
# Clone the repository
git clone <repository-url>
cd course_enrollment

# Install all dependencies
pip install -r requirements.txt
```

### Individual University Setup

#### Princeton
```bash
cd princeton/
pip install -r requirements.txt
python princeton_enrollment_scraper.py
```

#### Stanford
```bash
cd stanford/
pip install -r requirements.txt
python stanford_enrollment_scraper.py
```

#### Harvard
```bash
cd harvard/
# Data already collected - 24 CSV files with enrollment data
# Files follow naming: harvard_enrollment_YYYY_YYYY_semester.csv
# Source: Harvard FAS Registrar's Office enrollment reports
```

## Technical Notes

- **Rate limiting is essential** for successful scraping
- **Anti-scraping measures** may require adjustments to delays and headers
- **University websites** may change structure, requiring scraper updates
- **Data availability** varies by university and academic year
- **Session management** may be required for some universities
- **Error handling** includes retry logic and graceful recovery

## Expected Data Volumes

### Princeton
- **~11,000+ courses** across 7 academic terms
- **102+ departments** identified in recent data
- **7 academic terms** from Fall 2021-22 to Fall 2025-26
- **Complete enrollment data** with enrollment counts and course metadata

### Stanford
- **~10,000-15,000 courses** across all academic years
- **~200+ departments** across all schools
- **~7 schools** (Engineering, Humanities & Sciences, Business, Medicine, Law, Education, Sustainability)
- **Enrollment data** for courses that have it available

### Harvard
- **24 enrollment reports** across 13 academic years (2013-2026)
- **~200+ courses** per semester
- **Complete enrollment data** including UGrad, Grad, NonDegree, XReg, VUS, Employee counts
- **Course details** including Course ID, Title, Department, Instructor, Section Code

## Project Structure

```
course_enrollment/
├── .gitignore                   # Git ignore rules
├── README.md                    # This file
├── stanford/                    # Stanford University data and scraper
│   ├── stanford_enrollment_scraper.py
│   ├── requirements.txt
│   ├── stanford_enrollment.csv
│   └── stanford_enrollment.json
├── princeton/                   # Princeton University data and scraper
│   ├── princeton_enrollment_scraper.py
│   ├── requirements.txt
│   ├── princeton_enrollment.csv
│   └── princeton_enrollment.json
└── harvard/                     # Harvard University (data collected)
    └── harvard_enrollment_YYYY_YYYY_semester.csv (24 files)
```

## Legal and Ethical Considerations

- **Respectful scraping**: Built-in rate limiting and delays
- **Public data**: Only accessing publicly available information
- **Educational use**: Designed for research and educational purposes
- **Terms of service**: Use in accordance with each university's terms of service

## Contributing

When adding new universities:
1. Create a new subfolder with university name
2. Include scraper script, requirements, and documentation
3. Update this README with university status and instructions
4. Follow the established data field standards
5. Implement appropriate rate limiting and error handling
6. Document any university-specific technical requirements
7. Test thoroughly with rate limiting before full deployment
