"""
Data Cleaner for Course Recommendation System

Cleans and preprocesses course data from Coursera/Udemy/other sources.
Standardizes difficulty levels, extracts skills, and prepares data for database.
"""

import os
import re
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from pathlib import Path


class DataCleaner:
    """Cleans and preprocesses course data."""

    # Standard difficulty levels
    DIFFICULTY_MAPPING = {
        'beginner': 'Beginner',
        'intermediate': 'Intermediate',
        'advanced': 'Advanced',
        'mixed': 'Mixed',
        'beginner level': 'Beginner',
        'intermediate level': 'Intermediate',
        'advanced level': 'Advanced',
    }

    # Common skills to extract from descriptions
    SKILL_KEYWORDS = [
        'python', 'java', 'javascript', 'r', 'sql', 'machine learning',
        'deep learning', 'data science', 'statistics', 'probability',
        'algorithms', 'data structures', 'web development', 'frontend',
        'backend', 'database', 'cloud', 'aws', 'azure', 'docker',
        'kubernetes', 'git', 'agile', 'scrum', 'leadership', 'management',
        'marketing', 'finance', 'accounting', 'business analytics',
        'excel', 'powerbi', 'tableau', 'tensorflow', 'pytorch', 'nlp',
        'computer vision', 'reinforcement learning', 'cybersecurity',
        'networking', 'linux', 'devops', 'ci/cd', 'react', 'angular',
        'vue', 'node', 'django', 'flask', 'spring', 'api', 'rest',
        'graphql', 'mongodb', 'postgresql', 'mysql', 'redis', 'spark',
        'hadoop', 'data engineering', 'etl', 'data visualization',
        'project management', 'communication', 'problem solving'
    ]

    def __init__(self, raw_data_path: str = "data/raw", processed_data_path: str = "data/processed"):
        """Initialize data cleaner.

        Args:
            raw_data_path: Path to raw data files
            processed_data_path: Path to save processed data
        """
        self.raw_data_path = Path(raw_data_path)
        self.processed_data_path = Path(processed_data_path)

        # Create directories if they don't exist
        self.raw_data_path.mkdir(parents=True, exist_ok=True)
        self.processed_data_path.mkdir(parents=True, exist_ok=True)

    def clean_text(self, text: str) -> str:
        """Clean text data.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        if pd.isna(text) or text is None:
            return ""

        # Convert to string
        text = str(text)

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?-]', '', text)

        return text

    def standardize_difficulty(self, difficulty: str) -> str:
        """Standardize difficulty level.

        Args:
            difficulty: Raw difficulty string

        Returns:
            Standardized difficulty level
        """
        if pd.isna(difficulty) or difficulty is None:
            return "Mixed"

        difficulty = str(difficulty).lower().strip()

        # Check mapping
        for key, value in self.DIFFICULTY_MAPPING.items():
            if key in difficulty:
                return value

        # Default to Mixed
        return "Mixed"

    def extract_skills(self, text: str) -> List[str]:
        """Extract skills from course description.

        Args:
            text: Course description

        Returns:
            List of extracted skills
        """
        if pd.isna(text) or text is None:
            return []

        text = str(text).lower()
        found_skills = []

        for skill in self.SKILL_KEYWORDS:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text):
                found_skills.append(skill)

        return found_skills

    def extract_hours(self, text: str) -> Optional[float]:
        """Extract estimated hours from text.

        Args:
            text: Text containing hour information

        Returns:
            Estimated hours or None
        """
        if pd.isna(text) or text is None:
            return None

        text = str(text).lower()

        # Look for patterns like "10 hours", "20-30 hours", "approximately 15 hours"
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:-\s*\d+(?:\.\d+)?)?\s*hours?',
            r'(\d+(?:\.\d+)?)\s*(?:-\s*\d+(?:\.\d+)?)?\s*hrs?',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue

        return None

    def infer_category(self, course_name: str, description: str) -> str:
        """Infer course category from name and description.

        Args:
            course_name: Course name
            description: Course description

        Returns:
            Inferred category
        """
        combined_text = f"{course_name} {description}".lower()

        categories = {
            'Data Science': ['data science', 'data analytics', 'big data'],
            'Machine Learning': ['machine learning', 'ml', 'deep learning', 'ai', 'artificial intelligence'],
            'Programming': ['programming', 'coding', 'software development', 'python', 'java', 'javascript'],
            'Web Development': ['web development', 'frontend', 'backend', 'fullstack', 'web design'],
            'Business': ['business', 'management', 'leadership', 'marketing', 'finance', 'mba'],
            'Cloud Computing': ['cloud', 'aws', 'azure', 'gcp', 'devops'],
            'Cybersecurity': ['cybersecurity', 'security', 'ethical hacking', 'penetration testing'],
            'Data Engineering': ['data engineering', 'etl', 'data pipeline', 'data warehouse'],
            'Design': ['design', 'ui/ux', 'graphic design', 'user experience'],
            'Other': []
        }

        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in combined_text:
                    return category

        return 'Other'

    def clean_coursera_data(self, file_path: str) -> pd.DataFrame:
        """Clean Coursera course data.

        Args:
            file_path: Path to raw Coursera CSV file

        Returns:
            Cleaned DataFrame
        """
        print(f"Loading data from: {file_path}")
        df = pd.read_csv(file_path)

        print(f"Raw data shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")

        # Create clean dataframe
        clean_df = pd.DataFrame()

        # Map columns (adjust based on your dataset structure)
        column_mapping = {
            'course_name': ['Course Name', 'name', 'title', 'course_title'],
            'university': ['University', 'organization', 'provider'],
            'difficulty_level': ['Difficulty Level', 'difficulty', 'level'],
            'course_rating': ['Course Rating', 'rating', 'stars'],
            'course_url': ['Course URL', 'url', 'link'],
            'course_description': ['Course Description', 'description', 'summary'],
        }

        # Find and map columns
        for target_col, possible_names in column_mapping.items():
            for col_name in possible_names:
                if col_name in df.columns:
                    clean_df[target_col] = df[col_name]
                    break

        # If no mapping found, try case-insensitive matching
        if 'course_name' not in clean_df.columns:
            for col in df.columns:
                if 'name' in col.lower() or 'title' in col.lower():
                    clean_df['course_name'] = df[col]
                    break

        # Ensure required columns exist
        required_cols = ['course_name']
        for col in required_cols:
            if col not in clean_df.columns:
                raise ValueError(f"Required column '{col}' not found in dataset")

        # Clean text fields
        print("\nCleaning text fields...")
        for col in ['course_name', 'university', 'course_description']:
            if col in clean_df.columns:
                clean_df[col] = clean_df[col].apply(self.clean_text)

        # Standardize difficulty
        print("Standardizing difficulty levels...")
        if 'difficulty_level' in clean_df.columns:
            clean_df['difficulty_level'] = clean_df['difficulty_level'].apply(
                self.standardize_difficulty
            )
        else:
            clean_df['difficulty_level'] = 'Mixed'

        # Clean ratings
        print("Cleaning ratings...")
        if 'course_rating' in clean_df.columns:
            clean_df['course_rating'] = pd.to_numeric(
                clean_df['course_rating'], errors='coerce'
            )

        # Extract skills
        print("Extracting skills...")
        if 'course_description' in clean_df.columns:
            clean_df['extracted_skills'] = clean_df['course_description'].apply(
                self.extract_skills
            )
            clean_df['skills_count'] = clean_df['extracted_skills'].apply(len)

        # Infer category
        print("Inferring categories...")
        if 'course_description' in clean_df.columns and 'course_name' in clean_df.columns:
            clean_df['category'] = clean_df.apply(
                lambda row: self.infer_category(
                    row['course_name'],
                    row.get('course_description', '')
                ),
                axis=1
            )

        # Extract estimated hours (if available)
        if 'course_description' in clean_df.columns:
            clean_df['estimated_hours'] = clean_df['course_description'].apply(
                self.extract_hours
            )

        # Remove duplicates
        print("\nRemoving duplicates...")
        original_count = len(clean_df)
        clean_df = clean_df.drop_duplicates(subset=['course_name', 'university'])
        removed = original_count - len(clean_df)
        print(f"Removed {removed} duplicate courses")

        # Remove rows with missing course names
        clean_df = clean_df[clean_df['course_name'].str.strip() != '']

        print(f"\nCleaned data shape: {clean_df.shape}")

        return clean_df

    def save_cleaned_data(self, df: pd.DataFrame, filename: str = "cleaned_courses.csv"):
        """Save cleaned data to CSV.

        Args:
            df: Cleaned DataFrame
            filename: Output filename
        """
        output_path = self.processed_data_path / filename
        df.to_csv(output_path, index=False)
        print(f"\nCleaned data saved to: {output_path}")

        # Also save a summary
        summary_path = self.processed_data_path / "data_summary.txt"
        with open(summary_path, 'w') as f:
            f.write("DATA CLEANING SUMMARY\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Total courses: {len(df)}\n\n")
            f.write(f"Columns: {df.columns.tolist()}\n\n")

            if 'difficulty_level' in df.columns:
                f.write("Difficulty distribution:\n")
                f.write(df['difficulty_level'].value_counts().to_string())
                f.write("\n\n")

            if 'category' in df.columns:
                f.write("Category distribution:\n")
                f.write(df['category'].value_counts().to_string())
                f.write("\n\n")

            if 'course_rating' in df.columns:
                f.write(f"Average rating: {df['course_rating'].mean():.2f}\n")
                f.write(f"Rating range: {df['course_rating'].min():.1f} - {df['course_rating'].max():.1f}\n\n")

        print(f"Summary saved to: {summary_path}")


def test_cleaner():
    """Test data cleaner with sample data."""
    print("="*60)
    print("TESTING DATA CLEANER")
    print("="*60)

    # Create sample data
    sample_data = {
        'Course Name': ['Introduction to Python Programming', 'Machine Learning A-Z', 'Web Development Bootcamp'],
        'University': ['MIT', 'Stanford', 'Udemy'],
        'Difficulty Level': ['beginner level', 'intermediate', 'MIXED'],
        'Course Rating': ['4.5', '4.8', '4.2'],
        'Course Description': [
            'Learn Python programming from scratch. Covers basics of Python, data structures, and algorithms.',
            'Complete ML course covering supervised learning, unsupervised learning, and deep learning with TensorFlow.',
            'Fullstack web development with HTML, CSS, JavaScript, React, Node.js and MongoDB.'
        ]
    }

    # Create temporary CSV
    temp_csv = Path('data/raw/temp_sample.csv')
    temp_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(sample_data).to_csv(temp_csv, index=False)

    # Clean data
    cleaner = DataCleaner()
    clean_df = cleaner.clean_coursera_data(str(temp_csv))

    # Display results
    print("\nCleaned Data:")
    print(clean_df[['course_name', 'difficulty_level', 'category', 'skills_count']].to_string())

    print("\nExtracted skills for first course:")
    print(clean_df['extracted_skills'].iloc[0])

    # Clean up
    temp_csv.unlink()

    print("\n" + "="*60)
    print("Data cleaner test completed!")
    print("="*60)


if __name__ == "__main__":
    test_cleaner()
