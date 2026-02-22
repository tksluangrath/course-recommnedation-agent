"""
API Configuration for Course Data Collection

Handles configuration for:
- Coursera API (OAuth2 client credentials)
"""

import os
from dotenv import load_dotenv

load_dotenv()


class APIConfig:
    """Configuration for course platform APIs."""

    # Coursera API (OAuth2 client credentials)
    COURSERA_CLIENT_ID = os.getenv("COURSERA_CLIENT_ID", "")
    COURSERA_CLIENT_SECRET = os.getenv("COURSERA_CLIENT_SECRET", "")
    COURSERA_BASE_URL = "https://api.coursera.org/api"

    @staticmethod
    def is_coursera_configured() -> bool:
        """Check if Coursera API is configured."""
        return bool(APIConfig.COURSERA_CLIENT_ID and APIConfig.COURSERA_CLIENT_SECRET)

    @staticmethod
    def print_setup_instructions():
        """Print API setup instructions."""
        print("="*60)
        print("API CONFIGURATION STATUS")
        print("="*60)

        print("\nCOURSERA API:")
        if APIConfig.is_coursera_configured():
            print("  [OK] Configured (OAuth2 client credentials)")
        else:
            print("  [NOT CONFIGURED]")
            print("  To set up Coursera API:")
            print("  1. Register at: https://www.coursera.org/about/programs/api")
            print("  2. Get OAuth2 credentials")
            print("  3. Add to .env file:")
            print("     COURSERA_CLIENT_ID=your_client_id")
            print("     COURSERA_CLIENT_SECRET=your_client_secret")

        print("\n" + "="*60)
        print("DATA SOURCES:")
        print("="*60)
        print("1. Coursera API (recommended if configured)")
        print("   Run: python src/utils/coursera_api.py")
        print("2. Kaggle dataset (2025 Coursera dataset)")
        print("   https://www.kaggle.com/datasets/yosefxx590/coursera-courses-and-skills-dataset-2025")
        print("="*60)


class APICollector:
    """Collects course data from Coursera API."""

    def __init__(self):
        self.config = APIConfig()

    def collect_coursera_courses(self) -> list:
        """Placeholder — use the Kaggle dataset or coursera_api module instead."""
        print("[INFO] Use the Kaggle dataset or api_collectors.py instead:")
        print("https://www.kaggle.com/datasets/yosefxx590/coursera-courses-and-skills-dataset-2025")
        return []

    def print_recommendations(self):
        """Print data collection recommendations."""
        print("\n" + "="*60)
        print("DATA COLLECTION RECOMMENDATIONS")
        print("="*60)
        print("\n1. COURSERA DATASET (Recommended)")
        print("   URL: https://www.kaggle.com/datasets/yosefxx590/coursera-courses-and-skills-dataset-2025")
        print("   Download and place in: data/raw/coursera_courses_2025.csv")
        print("\n2. COURSERA API (if configured)")
        print("   Run: python src/utils/api_collectors.py")
        print("   Requires OAuth2 credentials in .env")
        print("\n" + "="*60)
        print("QUICK START:")
        print("="*60)
        print("1. Download Coursera dataset from Kaggle link above")
        print("2. Run: python src/utils/data_cleaner.py")
        print("3. Run: python src/utils/load_data_to_db.py")
        print("4. Run: python src/utils/embeddings.py")
        print("="*60 + "\n")


if __name__ == "__main__":
    APIConfig.print_setup_instructions()
