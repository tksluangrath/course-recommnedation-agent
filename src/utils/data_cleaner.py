"""
Data Cleaner for Course Recommendation System

Cleans and preprocesses Coursera course data.
Standardizes difficulty levels, extracts skills, and prepares data for database.
"""

import re
import pandas as pd
import numpy as np
from typing import List, Optional
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

    # Duration string to approximate hours mapping
    DURATION_MAPPING = {
        'less than 2 hours': 1.0,
        '1 - 4 weeks': 20.0,
        '1 - 3 months': 60.0,
        '3 - 6 months': 120.0,
        '6 - 12 months': 240.0,
    }

    def __init__(self, raw_data_path: str = "data/raw", processed_data_path: str = "data/processed"):
        self.raw_data_path = Path(raw_data_path)
        self.processed_data_path = Path(processed_data_path)
        self.raw_data_path.mkdir(parents=True, exist_ok=True)
        self.processed_data_path.mkdir(parents=True, exist_ok=True)

    def clean_text(self, text: str) -> str:
        """Clean text data."""
        if pd.isna(text) or text is None:
            return ""
        text = str(text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def standardize_difficulty(self, difficulty: str) -> str:
        """Standardize difficulty level."""
        if pd.isna(difficulty) or difficulty is None:
            return "Mixed"
        difficulty = str(difficulty).lower().strip()
        for key, value in self.DIFFICULTY_MAPPING.items():
            if key in difficulty:
                return value
        return "Mixed"

    def parse_duration(self, duration: str) -> Optional[float]:
        """Parse duration string to estimated hours.

        Handles formats like: "Less Than 2 Hours", "1 - 4 Weeks", "1 - 3 Months"
        """
        if pd.isna(duration) or duration is None:
            return None
        duration_lower = str(duration).lower().strip()
        for key, hours in self.DURATION_MAPPING.items():
            if key in duration_lower:
                return hours
        # Try extracting numeric hours directly
        match = re.search(r'(\d+(?:\.\d+)?)\s*hours?', duration_lower)
        if match:
            return float(match.group(1))
        return None

    def parse_reviews(self, reviews) -> Optional[int]:
        """Parse review count strings like '6100', '11K', '30K'."""
        if pd.isna(reviews) or reviews is None:
            return None
        text = str(reviews).strip().lower().replace(',', '')
        if 'k' in text:
            try:
                return int(float(text.replace('k', '')) * 1000)
            except ValueError:
                return None
        try:
            return int(float(text))
        except ValueError:
            return None

    def parse_gained_skills(self, skills_str: str) -> List[str]:
        """Parse comma-separated skills string into a list."""
        if pd.isna(skills_str) or skills_str is None:
            return []
        return [s.strip() for s in str(skills_str).split(',') if s.strip()]

    def clean_coursera_data(self, file_path: str) -> pd.DataFrame:
        """Clean Coursera course data.

        Handles both the 2025 dataset format (Title, Institution, Level, Rate,
        Subject, Gained Skills, Duration, Reviews, Learning Product) and older
        formats (Course Name, University, Difficulty Level, Course Rating, etc.).
        """
        print(f"Loading data from: {file_path}")
        df = pd.read_csv(file_path)

        print(f"Raw data shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")

        clean_df = pd.DataFrame()

        # Column mapping: internal name -> list of possible source column names
        column_mapping = {
            'course_name': ['Title', 'Course Name', 'name', 'title', 'course_title'],
            'university': ['Institution', 'University', 'organization', 'provider'],
            'difficulty_level': ['Level', 'Difficulty Level', 'difficulty', 'level'],
            'course_rating': ['Rate', 'Course Rating', 'rating', 'stars'],
            'course_url': ['Course URL', 'url', 'link'],
            'course_description': ['Course Description', 'description', 'summary'],
            'category': ['Subject'],
            'gained_skills': ['Gained Skills'],
            'duration': ['Duration'],
            'num_reviews': ['Reviews'],
            'learning_product': ['Learning Product'],
        }

        # Find and map columns
        for target_col, possible_names in column_mapping.items():
            for col_name in possible_names:
                if col_name in df.columns:
                    clean_df[target_col] = df[col_name]
                    break

        # Fallback: case-insensitive matching for course_name
        if 'course_name' not in clean_df.columns:
            for col in df.columns:
                if 'name' in col.lower() or 'title' in col.lower():
                    clean_df['course_name'] = df[col]
                    break

        # Ensure required columns exist
        if 'course_name' not in clean_df.columns:
            raise ValueError("Required column 'course_name' not found in dataset")

        # Clean text fields
        print("\nCleaning text fields...")
        for col in ['course_name', 'university', 'course_description', 'category']:
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

        # Parse review counts
        if 'num_reviews' in clean_df.columns:
            print("Parsing review counts...")
            clean_df['num_reviews'] = clean_df['num_reviews'].apply(self.parse_reviews)

        # Parse duration to estimated hours
        if 'duration' in clean_df.columns:
            print("Parsing durations...")
            clean_df['estimated_hours'] = clean_df['duration'].apply(self.parse_duration)
            clean_df.drop(columns=['duration'], inplace=True)

        # Handle skills: prefer pre-extracted "Gained Skills" over keyword extraction
        print("Processing skills...")
        if 'gained_skills' in clean_df.columns:
            clean_df['extracted_skills'] = clean_df['gained_skills'].apply(
                self.parse_gained_skills
            )
            clean_df['skills_count'] = clean_df['extracted_skills'].apply(len)
            clean_df.drop(columns=['gained_skills'], inplace=True)

        # Build a synthetic description for embeddings if none exists
        # Combines title + category + skills for rich semantic search
        if 'course_description' not in clean_df.columns or clean_df['course_description'].isna().all():
            print("No description column found, building from title + category + skills...")
            def build_description(row):
                parts = [str(row.get('course_name', ''))]
                if pd.notna(row.get('category')):
                    parts.append(str(row['category']))
                if 'extracted_skills' in row.index and row.get('extracted_skills'):
                    skills = row['extracted_skills']
                    if isinstance(skills, list):
                        parts.append("Skills: " + ", ".join(skills))
                return ". ".join(parts)

            clean_df['course_description'] = clean_df.apply(build_description, axis=1)

        # Use Subject as category if available, otherwise infer
        if 'category' not in clean_df.columns or clean_df['category'].isna().all():
            print("Inferring categories...")
            clean_df['category'] = clean_df.apply(
                lambda row: self._infer_category(
                    row.get('course_name', ''),
                    row.get('course_description', '')
                ),
                axis=1
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

    def _infer_category(self, course_name: str, description: str) -> str:
        """Infer course category from name and description."""
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
        }
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in combined_text:
                    return category
        return 'Other'

    def download_sample_data(self, save_path: str = None) -> pd.DataFrame:
        """Create a small synthetic dataset for testing when no real data is available.

        Args:
            save_path: Path to save sample data (default: data/raw/sample_courses.csv)

        Returns:
            DataFrame with 20 sample courses
        """
        if save_path is None:
            save_path = self.raw_data_path / "sample_courses.csv"

        print("Creating sample course data for testing...")

        sample_data = {
            'Title': [
                'Machine Learning Specialization', 'Deep Learning Specialization',
                'Python for Everybody', 'Data Science Professional Certificate',
                'Full Stack Web Development', 'Digital Marketing Specialization',
                'Financial Markets', 'Introduction to Psychology',
                'Cloud Computing Fundamentals', 'Cybersecurity Specialization',
                'Introduction to Artificial Intelligence', 'Data Structures and Algorithms',
                'Business Analytics Specialization', 'Excel Skills for Business',
                'Project Management Professional', 'UX Design Specialization',
                'SQL for Data Science', 'R Programming',
                'TensorFlow Developer Certificate', 'AWS Cloud Practitioner'
            ],
            'Institution': [
                'Stanford University', 'DeepLearning.AI', 'University of Michigan', 'IBM',
                'Meta', 'University of Illinois', 'Yale University', 'Yale University',
                'Google Cloud', 'University of Maryland', 'Stanford University', 'UC San Diego',
                'University of Pennsylvania', 'Macquarie University', 'Google', 'Google',
                'UC Davis', 'Johns Hopkins University', 'DeepLearning.AI', 'Amazon Web Services'
            ],
            'Level': [
                'Intermediate', 'Advanced', 'Beginner', 'Beginner', 'Intermediate',
                'Beginner', 'Beginner', 'Beginner', 'Beginner', 'Intermediate',
                'Intermediate', 'Intermediate', 'Beginner', 'Beginner', 'Intermediate',
                'Beginner', 'Beginner', 'Beginner', 'Intermediate', 'Beginner'
            ],
            'Rate': [4.9, 4.8, 4.8, 4.7, 4.6, 4.7, 4.8, 4.9, 4.5, 4.6, 4.7, 4.6, 4.5, 4.7, 4.6, 4.8, 4.6, 4.5, 4.7, 4.6],
        }

        df = pd.DataFrame(sample_data)
        df.to_csv(save_path, index=False)

        print(f"Sample data created with {len(df)} courses")
        print(f"Saved to: {save_path}")

        return df

    def save_cleaned_data(self, df: pd.DataFrame, filename: str = "cleaned_courses.csv"):
        """Save cleaned data to CSV."""
        output_path = self.processed_data_path / filename
        df.to_csv(output_path, index=False)
        print(f"\nCleaned data saved to: {output_path}")

        # Save summary
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
                valid_ratings = df['course_rating'].dropna()
                if len(valid_ratings) > 0:
                    f.write(f"Average rating: {valid_ratings.mean():.2f}\n")
                    f.write(f"Rating range: {valid_ratings.min():.1f} - {valid_ratings.max():.1f}\n\n")

            if 'skills_count' in df.columns:
                f.write(f"Average skills per course: {df['skills_count'].mean():.1f}\n")
                f.write(f"Total unique skills: {len(set(s for skills in df['extracted_skills'] if isinstance(skills, list) for s in skills))}\n\n")

        print(f"Summary saved to: {summary_path}")


if __name__ == "__main__":
    # Clean the real Coursera 2025 dataset
    cleaner = DataCleaner()
    df = cleaner.clean_coursera_data('data/raw/coursera.csv')
    cleaner.save_cleaned_data(df)
