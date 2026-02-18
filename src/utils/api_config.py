"""
API Configuration for Course Data Collection

Placeholder for future API integrations with:
- Udemy API
- Coursera API
- Class Central
- Other course platforms

For now, we'll use Kaggle datasets instead.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class APIConfig:
    """Configuration for course platform APIs."""

    # Udemy API (requires affiliate account)
    UDEMY_CLIENT_ID = os.getenv("UDEMY_CLIENT_ID", "")
    UDEMY_CLIENT_SECRET = os.getenv("UDEMY_CLIENT_SECRET", "")
    UDEMY_BASE_URL = "https://www.udemy.com/api-2.0"

    # Coursera API (OAuth2 client credentials)
    COURSERA_CLIENT_ID = os.getenv("COURSERA_CLIENT_ID", "")
    COURSERA_CLIENT_SECRET = os.getenv("COURSERA_CLIENT_SECRET", "")
    COURSERA_BASE_URL = "https://api.coursera.org/api"

    # Class Central (web scraping or unofficial API)
    CLASS_CENTRAL_BASE_URL = "https://www.classcentral.com"

    @staticmethod
    def is_udemy_configured() -> bool:
        """Check if Udemy API is configured."""
        return bool(APIConfig.UDEMY_CLIENT_ID and APIConfig.UDEMY_CLIENT_SECRET)

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

        print("\nUDEMY API:")
        if APIConfig.is_udemy_configured():
            print("  [OK] Configured")
        else:
            print("  [NOT CONFIGURED]")
            print("  To set up Udemy API:")
            print("  1. Join Udemy Affiliate Program: https://www.udemy.com/affiliate/")
            print("  2. Get API credentials from affiliate dashboard")
            print("  3. Add to .env file:")
            print("     UDEMY_CLIENT_ID=your_client_id")
            print("     UDEMY_CLIENT_SECRET=your_client_secret")

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
        print("3. Udemy API (if configured)")
        print("="*60)


if __name__ == "__main__":
    APIConfig.print_setup_instructions()
