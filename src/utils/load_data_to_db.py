"""
Load cleaned course data into the database.

This script loads cleaned CSV data and populates the SQLite database.
"""

import ast
import pandas as pd
from database import DatabaseManager
from pathlib import Path


def load_courses_to_database(csv_path: str = "data/processed/cleaned_courses.csv"):
    """Load courses from cleaned CSV into database."""
    print("="*60)
    print("LOADING COURSES INTO DATABASE")
    print("="*60)

    if not Path(csv_path).exists():
        print(f"[ERROR] File not found: {csv_path}")
        print("Please run data_cleaner.py first to create cleaned data")
        return

    print(f"\nLoading cleaned data from: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} courses")

    # Delete old database to start fresh
    db_path = Path("data/courses.db")
    if db_path.exists():
        db_path.unlink()
        print("Removed old database")

    db = DatabaseManager()

    # Columns that map directly to the Course model
    course_columns = [
        'course_name', 'university', 'difficulty_level',
        'course_rating', 'course_url', 'course_description',
        'category', 'estimated_hours', 'num_reviews', 'learning_product'
    ]

    # Prepare course data
    courses_data = []
    for _, row in df.iterrows():
        course_dict = {}
        for col in course_columns:
            if col in df.columns and pd.notna(row.get(col)):
                course_dict[col] = row[col]
        if 'difficulty_level' not in course_dict:
            course_dict['difficulty_level'] = 'Mixed'
        courses_data.append(course_dict)

    print("\nAdding courses to database...")
    count = db.add_courses_batch(courses_data)

    # Link skills if available
    if 'extracted_skills' in df.columns:
        print("\nLinking skills to courses...")
        skill_count = 0

        for _, row in df.iterrows():
            if pd.isna(row.get('extracted_skills')):
                continue

            courses = db.search_courses(query=row['course_name'], limit=1)
            if not courses:
                continue

            course = courses[0]

            # Parse skills from string representation
            skills_raw = row['extracted_skills']
            if isinstance(skills_raw, str):
                try:
                    skills = ast.literal_eval(skills_raw)
                except (ValueError, SyntaxError):
                    skills = [s.strip() for s in skills_raw.split(',') if s.strip()]
            elif isinstance(skills_raw, list):
                skills = skills_raw
            else:
                continue

            for skill in skills:
                try:
                    db.link_course_skill(course.id, str(skill).strip())
                    skill_count += 1
                except Exception:
                    pass

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
