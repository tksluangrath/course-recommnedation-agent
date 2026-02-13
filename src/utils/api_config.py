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

    # Coursera API (limited public access)
    COURSERA_API_KEY = os.getenv("COURSERA_API_KEY", "")
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
        return bool(APIConfig.COURSERA_API_KEY)

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
            print("  [OK] Configured")
        else:
            print("  [NOT CONFIGURED]")
            print("  Note: Coursera has limited public API access")
            print("  Alternative: Use Kaggle datasets instead")

        print("\n" + "="*60)
        print("RECOMMENDATION:")
        print("="*60)
        print("For this project, we recommend using Kaggle datasets instead of APIs:")
        print("1. Coursera: https://www.kaggle.com/datasets/khusheekapoor/coursera-courses-dataset-2021")
        print("2. Udemy: https://www.kaggle.com/search?q=udemy+courses")
        print("\nDownload datasets and place them in data/raw/ directory")
        print("="*60)


if __name__ == "__main__":
    APIConfig.print_setup_instructions()
