"""
API Data Collector for Course Recommendation System

Placeholder for future API integrations.
Currently recommends using Kaggle datasets instead.
"""

from typing import List, Dict
import requests
from .api_config import APIConfig


class APICollector:
    """Collects course data from various APIs."""

    def __init__(self):
        """Initialize API collector."""
        self.config = APIConfig()

    def collect_udemy_courses(self, search_query: str = "python", max_results: int = 100) -> List[Dict]:
        """Collect courses from Udemy API.

        Args:
            search_query: Search term
            max_results: Maximum number of courses to fetch

        Returns:
            List of course dictionaries
        """
        if not APIConfig.is_udemy_configured():
            print("[ERROR] Udemy API not configured")
            print("Please see instructions by running: python src/utils/api_config.py")
            return []

        print(f"Fetching Udemy courses for: {search_query}")

        # Placeholder for actual API implementation
        # This would require authentication and proper API calls
        print("[INFO] Udemy API integration is a placeholder")
        print("[INFO] Please use Kaggle datasets instead")

        return []

    def collect_coursera_courses(self) -> List[Dict]:
        """Collect courses from Coursera.

        Returns:
            List of course dictionaries
        """
        print("[INFO] Coursera API has limited public access")
        print("[INFO] Please use Kaggle dataset instead:")
        print("https://www.kaggle.com/datasets/khusheekapoor/coursera-courses-dataset-2021")

        return []

    def print_recommendations(self):
        """Print data collection recommendations."""
        print("\n" + "="*60)
        print("DATA COLLECTION RECOMMENDATIONS")
        print("="*60)
        print("\nInstead of using APIs (which have limitations), we recommend:")
        print("\n1. COURSERA DATASET (Recommended)")
        print("   - URL: https://www.kaggle.com/datasets/khusheekapoor/coursera-courses-dataset-2021")
        print("   - Contains ~4000 courses")
        print("   - Download and place in: data/raw/Coursera.csv")

        print("\n2. UDEMY DATASETS")
        print("   - Search Kaggle for: 'udemy courses'")
        print("   - Multiple datasets available")
        print("   - Download and place in: data/raw/")

        print("\n3. CLASS CENTRAL")
        print("   - Manual export or web scraping")
        print("   - Aggregates courses from multiple platforms")

        print("\n" + "="*60)
        print("QUICK START:")
        print("="*60)
        print("1. Download Coursera dataset from link above")
        print("2. Place CSV file in data/raw/")
        print("3. Run: python src/utils/data_loader.py")
        print("4. Run: python src/utils/data_cleaner.py")
        print("="*60 + "\n")


if __name__ == "__main__":
    collector = APICollector()
    collector.print_recommendations()
