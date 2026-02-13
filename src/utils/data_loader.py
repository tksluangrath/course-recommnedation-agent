"""
Data Loader for Course Recommendation System

Handles loading course data from various sources:
- CSV files (Coursera, Udemy datasets from Kaggle)
- APIs (future implementation)
- Database exports
"""

import os
import pandas as pd
from pathlib import Path
from typing import Optional, List
import requests
from dotenv import load_dotenv

load_dotenv()


class DataLoader:
    """Loads course data from various sources."""

    def __init__(self, raw_data_path: str = "data/raw"):
        """Initialize data loader.

        Args:
            raw_data_path: Path to raw data directory
        """
        self.raw_data_path = Path(raw_data_path)
        self.raw_data_path.mkdir(parents=True, exist_ok=True)

    def load_csv(self, file_path: str) -> pd.DataFrame:
        """Load course data from CSV file.

        Args:
            file_path: Path to CSV file

        Returns:
            DataFrame with course data
        """
        print(f"Loading data from: {file_path}")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        df = pd.read_csv(file_path)
        print(f"Loaded {len(df)} courses from {file_path}")
        print(f"Columns: {df.columns.tolist()}")

        return df

    def load_coursera_kaggle(self, filename: str = "Coursera.csv") -> pd.DataFrame:
        """Load Coursera dataset from Kaggle.

        The expected dataset is from:
        https://www.kaggle.com/datasets/khusheekapoor/coursera-courses-dataset-2021

        Args:
            filename: Name of the CSV file in raw data directory

        Returns:
            DataFrame with Coursera courses
        """
        file_path = self.raw_data_path / filename

        if not file_path.exists():
            print(f"\n[WARNING] Coursera dataset not found at: {file_path}")
            print("\nTo get the dataset:")
            print("1. Go to: https://www.kaggle.com/datasets/khusheekapoor/coursera-courses-dataset-2021")
            print("2. Download the dataset")
            print(f"3. Place 'Coursera.csv' in: {self.raw_data_path}")
            print("\nAlternatively, run the data collector to fetch courses via API.")
            raise FileNotFoundError(f"Dataset not found: {file_path}")

        return self.load_csv(str(file_path))

    def load_udemy_kaggle(self, filename: str = "udemy_courses.csv") -> pd.DataFrame:
        """Load Udemy dataset from Kaggle.

        Args:
            filename: Name of the CSV file in raw data directory

        Returns:
            DataFrame with Udemy courses
        """
        file_path = self.raw_data_path / filename

        if not file_path.exists():
            print(f"\n[WARNING] Udemy dataset not found at: {file_path}")
            print("\nYou can download Udemy datasets from Kaggle")
            raise FileNotFoundError(f"Dataset not found: {file_path}")

        return self.load_csv(str(file_path))

    def load_all_sources(self) -> pd.DataFrame:
        """Load and combine data from all available sources.

        Returns:
            Combined DataFrame from all sources
        """
        dfs = []

        # Try loading Coursera
        try:
            coursera_df = self.load_coursera_kaggle()
            coursera_df['source'] = 'Coursera'
            dfs.append(coursera_df)
        except FileNotFoundError:
            print("Coursera dataset not loaded")

        # Try loading Udemy
        try:
            udemy_df = self.load_udemy_kaggle()
            udemy_df['source'] = 'Udemy'
            dfs.append(udemy_df)
        except FileNotFoundError:
            print("Udemy dataset not loaded")

        # Try loading any other CSV files in raw data directory
        for file_path in self.raw_data_path.glob("*.csv"):
            filename = file_path.name.lower()
            if filename not in ['coursera.csv', 'udemy_courses.csv']:
                try:
                    df = self.load_csv(str(file_path))
                    df['source'] = file_path.stem
                    dfs.append(df)
                    print(f"Loaded additional dataset: {file_path.name}")
                except Exception as e:
                    print(f"Failed to load {file_path.name}: {e}")

        if not dfs:
            raise ValueError("No course data found. Please add CSV files to data/raw/")

        # Combine all dataframes
        combined_df = pd.concat(dfs, ignore_index=True)
        print(f"\nTotal courses loaded from all sources: {len(combined_df)}")

        return combined_df

    def download_sample_data(self, save_path: Optional[str] = None):
        """Download a sample dataset for testing.

        This creates a small sample dataset if no real data is available.

        Args:
            save_path: Path to save sample data (default: data/raw/sample_courses.csv)
        """
        if save_path is None:
            save_path = self.raw_data_path / "sample_courses.csv"

        print("Creating sample course data for testing...")

        sample_data = {
            'Course Name': [
                'Machine Learning Specialization',
                'Deep Learning Specialization',
                'Python for Everybody',
                'Data Science Professional Certificate',
                'Full Stack Web Development',
                'Digital Marketing Specialization',
                'Financial Markets',
                'Introduction to Psychology',
                'Cloud Computing Fundamentals',
                'Cybersecurity Specialization',
                'Introduction to Artificial Intelligence',
                'Data Structures and Algorithms',
                'Business Analytics Specialization',
                'Excel Skills for Business',
                'Project Management Professional',
                'UX Design Specialization',
                'SQL for Data Science',
                'R Programming',
                'TensorFlow Developer Certificate',
                'AWS Cloud Practitioner'
            ],
            'University': [
                'Stanford University',
                'DeepLearning.AI',
                'University of Michigan',
                'IBM',
                'Meta',
                'University of Illinois',
                'Yale University',
                'Yale University',
                'Google Cloud',
                'University of Maryland',
                'Stanford University',
                'UC San Diego',
                'University of Pennsylvania',
                'Macquarie University',
                'Google',
                'Google',
                'UC Davis',
                'Johns Hopkins University',
                'DeepLearning.AI',
                'Amazon Web Services'
            ],
            'Difficulty Level': [
                'Intermediate',
                'Advanced',
                'Beginner',
                'Beginner',
                'Intermediate',
                'Beginner',
                'Beginner',
                'Beginner',
                'Beginner',
                'Intermediate',
                'Intermediate',
                'Intermediate',
                'Beginner',
                'Beginner',
                'Intermediate',
                'Beginner',
                'Beginner',
                'Beginner',
                'Intermediate',
                'Beginner'
            ],
            'Course Rating': [4.9, 4.8, 4.8, 4.7, 4.6, 4.7, 4.8, 4.9, 4.5, 4.6, 4.7, 4.6, 4.5, 4.7, 4.6, 4.8, 4.6, 4.5, 4.7, 4.6],
            'Course Description': [
                'Learn machine learning fundamentals including supervised and unsupervised learning, neural networks, and best practices for ML projects.',
                'Master deep learning with CNNs, RNNs, LSTMs, transformers, and deployment. Build neural networks using TensorFlow and PyTorch.',
                'Learn Python programming from scratch. Covers data structures, web scraping, databases, and data visualization.',
                'Launch your career in data science. Learn Python, SQL, data analysis, data visualization, and machine learning.',
                'Become a full-stack web developer. Learn HTML, CSS, JavaScript, React, Node.js, Express, and MongoDB.',
                'Learn digital marketing strategies including SEO, social media marketing, email marketing, and analytics.',
                'Understand financial markets, institutions, and instruments. Learn about stocks, bonds, derivatives, and behavioral finance.',
                'Introduction to psychological science covering brain, development, learning, memory, language, and social psychology.',
                'Learn cloud computing basics, virtualization, containerization, and cloud deployment with hands-on projects.',
                'Master cybersecurity fundamentals, cryptography, network security, and ethical hacking techniques.',
                'Introduction to AI covering search, optimization, logic, planning, learning, and neural networks.',
                'Learn fundamental data structures and algorithms. Covers sorting, searching, graphs, trees, and dynamic programming.',
                'Learn to use data for business decisions. Covers analytics, forecasting, optimization, and data-driven management.',
                'Master Excel for business analytics, data visualization, pivot tables, VBA, and advanced formulas.',
                'Prepare for PMP certification. Learn project planning, execution, monitoring, risk management, and agile methodologies.',
                'Learn user experience design process including research, wireframing, prototyping, and usability testing.',
                'Learn SQL for data analysis. Covers queries, joins, aggregations, subqueries, and working with large datasets.',
                'Learn R programming for statistical analysis and data visualization. Covers data manipulation and ggplot2.',
                'Prepare for TensorFlow Developer Certification. Build and train neural networks for computer vision and NLP.',
                'Prepare for AWS Cloud Practitioner certification. Learn cloud concepts, security, architecture, and pricing.'
            ]
        }

        df = pd.DataFrame(sample_data)
        df.to_csv(save_path, index=False)

        print(f"Sample data created with {len(df)} courses")
        print(f"Saved to: {save_path}")

        return df


def test_loader():
    """Test data loader functionality."""
    print("="*60)
    print("TESTING DATA LOADER")
    print("="*60)

    loader = DataLoader()

    # Try to load Coursera dataset
    print("\n1. Attempting to load Coursera dataset...")
    try:
        df = loader.load_coursera_kaggle()
        print(f"Successfully loaded Coursera data: {len(df)} courses")
        print(f"Columns: {df.columns.tolist()}")
    except FileNotFoundError:
        print("Coursera dataset not found. Creating sample data instead...")
        df = loader.download_sample_data()

    # Display sample
    print("\n2. Sample courses:")
    if 'Course Name' in df.columns:
        print(df[['Course Name', 'University', 'Difficulty Level']].head())
    elif 'course_name' in df.columns:
        print(df[['course_name', 'university', 'difficulty_level']].head())
    else:
        print(df.head())

    print("\n" + "="*60)
    print("Data loader test completed!")
    print("="*60)


if __name__ == "__main__":
    test_loader()
