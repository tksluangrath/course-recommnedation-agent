"""
Load cleaned course data into the database.

This script loads cleaned CSV data and populates the SQLite database.
"""

import pandas as pd
from database import DatabaseManager
from pathlib import Path


def load_courses_to_database(csv_path: str = "data/processed/cleaned_courses.csv"):
    """Load courses from cleaned CSV into database.

    Args:
        csv_path: Path to cleaned courses CSV
    """
    print("="*60)
    print("LOADING COURSES INTO DATABASE")
    print("="*60)

    # Check if file exists
    if not Path(csv_path).exists():
        print(f"[ERROR] File not found: {csv_path}")
        print("Please run data_cleaner.py first to create cleaned data")
        return

    # Load cleaned data
    print(f"\nLoading cleaned data from: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} courses")

    # Initialize database
    db = DatabaseManager()

    # Map DataFrame columns to Course model fields
    course_columns = [
        'course_name',
        'university',
        'difficulty_level',
        'course_rating',
        'course_url',
        'course_description',
        'category',
        'estimated_hours'
    ]

    # Filter and prepare data
    courses_data = []
    for _, row in df.iterrows():
        course_dict = {}
        for col in course_columns:
            if col in df.columns:
                value = row[col]
                # Handle NaN values
                if pd.notna(value):
                    course_dict[col] = value
            else:
                # Handle missing columns with defaults
                if col == 'difficulty_level':
                    course_dict[col] = 'Mixed'

        courses_data.append(course_dict)

    # Add courses to database
    print("\nAdding courses to database...")
    count = db.add_courses_batch(courses_data)

    # Link skills if available
    if 'extracted_skills' in df.columns:
        print("\nLinking skills to courses...")
        skill_count = 0

        for idx, row in df.iterrows():
            if pd.notna(row.get('extracted_skills')):
                # Get the course from database
                courses = db.search_courses(query=row['course_name'], limit=1)
                if courses:
                    course = courses[0]

                    # Parse skills (assuming they're stored as string representation of list)
                    skills = eval(row['extracted_skills']) if isinstance(row['extracted_skills'], str) else row['extracted_skills']

                    for skill in skills:
                        try:
                            db.link_course_skill(course.id, skill)
                            skill_count += 1
                        except Exception as e:
                            print(f"Error linking skill '{skill}': {e}")

        print(f"Linked {skill_count} skills to courses")

    # Display statistics
    print("\n" + "="*60)
    print("DATABASE STATISTICS")
    print("="*60)
    stats = db.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")

    print("\n" + "="*60)
    print("Data loaded successfully!")
    print("="*60)


if __name__ == "__main__":
    load_courses_to_database()
