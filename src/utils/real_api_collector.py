"""
Real API Data Collector for Course Platforms

Fetches real course data from various platforms:
1. Udemy API (affiliate program - requires credentials)
2. Coursera (web scraping - no official API)
3. edX (web scraping)
4. Class Central (aggregator)
5. YouTube API (free courses)
"""

import os
import json
import time
import requests
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd

load_dotenv()


class RealAPICollector:
    """Fetches real course data from various platforms."""

    def __init__(self, output_dir: str = "data/raw"):
        """Initialize API collector.

        Args:
            output_dir: Directory to save fetched data
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # API credentials
        self.udemy_client_id = os.getenv("UDEMY_CLIENT_ID", "")
        self.udemy_client_secret = os.getenv("UDEMY_CLIENT_SECRET", "")
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY", "")

    # ==================== UDEMY API ====================

    def fetch_udemy_courses(
        self,
        search_query: str = "programming",
        max_courses: int = 100,
        language: str = "en"
    ) -> List[Dict]:
        """Fetch courses from Udemy API.

        Requires Udemy affiliate account:
        https://www.udemy.com/affiliate/

        Args:
            search_query: Search term
            max_courses: Maximum courses to fetch
            language: Course language

        Returns:
            List of course dictionaries
        """
        if not self.udemy_client_id or not self.udemy_client_secret:
            print("\n[ERROR] Udemy API credentials not configured")
            print("\nTo use Udemy API:")
            print("1. Sign up for Udemy Affiliate Program: https://www.udemy.com/affiliate/")
            print("2. Get API credentials from affiliate dashboard")
            print("3. Add to .env file:")
            print("   UDEMY_CLIENT_ID=your_client_id")
            print("   UDEMY_CLIENT_SECRET=your_client_secret")
            return []

        print(f"Fetching Udemy courses for: {search_query}")

        courses = []
        page = 1
        page_size = 100  # Max allowed by Udemy

        while len(courses) < max_courses:
            url = "https://www.udemy.com/api-2.0/courses/"

            params = {
                'search': search_query,
                'page': page,
                'page_size': min(page_size, max_courses - len(courses)),
                'language': language,
                'ordering': 'most-reviewed'
            }

            try:
                response = requests.get(
                    url,
                    auth=(self.udemy_client_id, self.udemy_client_secret),
                    params=params
                )

                if response.status_code != 200:
                    print(f"Error: {response.status_code} - {response.text}")
                    break

                data = response.json()

                if not data.get('results'):
                    break

                for course in data['results']:
                    courses.append({
                        'course_name': course.get('title'),
                        'university': 'Udemy',
                        'difficulty_level': self._map_udemy_difficulty(course.get('instructional_level')),
                        'course_rating': course.get('rating'),
                        'course_url': f"https://www.udemy.com{course.get('url')}",
                        'course_description': course.get('headline', ''),
                        'price': course.get('price'),
                        'num_reviews': course.get('num_reviews'),
                        'num_subscribers': course.get('num_subscribers'),
                        'source': 'Udemy'
                    })

                print(f"Fetched {len(courses)} courses so far...")

                # Check if there are more pages
                if not data.get('next'):
                    break

                page += 1
                time.sleep(0.5)  # Rate limiting

            except Exception as e:
                print(f"Error fetching Udemy courses: {e}")
                break

        print(f"\nTotal Udemy courses fetched: {len(courses)}")
        return courses

    def _map_udemy_difficulty(self, level: str) -> str:
        """Map Udemy difficulty levels to standard format."""
        mapping = {
            'all': 'Beginner',
            'beginner': 'Beginner',
            'intermediate': 'Intermediate',
            'expert': 'Advanced'
        }
        return mapping.get(level.lower() if level else '', 'Mixed')

    # ==================== COURSERA (Web Scraping) ====================

    def fetch_coursera_catalog(self, max_courses: int = 1000) -> List[Dict]:
        """Fetch Coursera catalog via web scraping.

        Note: Since Coursera doesn't have a public API, this uses
        their public catalog data. For large datasets, use Kaggle instead.

        Args:
            max_courses: Maximum courses to fetch

        Returns:
            List of course dictionaries
        """
        print("\n[INFO] Coursera doesn't have a public API")
        print("\nRecommended approach:")
        print("1. Download dataset from Kaggle:")
        print("   https://www.kaggle.com/datasets/khusheekapoor/coursera-courses-dataset-2021")
        print("2. Place CSV in: data/raw/Coursera.csv")
        print("3. Or use the Coursera Catalog API (requires special access)")

        return []

    # ==================== EDX (Web Scraping) ====================

    def fetch_edx_courses(self, max_courses: int = 100) -> List[Dict]:
        """Fetch edX courses using their search API.

        edX has a public search API that can be used without authentication.

        Args:
            max_courses: Maximum courses to fetch

        Returns:
            List of course dictionaries
        """
        print("Fetching edX courses...")

        courses = []
        page = 0
        page_size = 50

        while len(courses) < max_courses:
            url = "https://www.edx.org/api/v1/catalog/search"

            params = {
                'page': page,
                'page_size': page_size,
                'content_type': 'course'
            }

            try:
                response = requests.get(url, params=params, timeout=10)

                if response.status_code != 200:
                    print(f"Error: {response.status_code}")
                    break

                data = response.json()

                if not data.get('results'):
                    break

                for course in data['results']:
                    courses.append({
                        'course_name': course.get('title'),
                        'university': course.get('partners', [{}])[0].get('name', 'edX'),
                        'difficulty_level': self._map_edx_difficulty(course.get('level_type')),
                        'course_rating': None,  # edX doesn't provide ratings in API
                        'course_url': f"https://www.edx.org{course.get('marketing_url', '')}",
                        'course_description': course.get('short_description', ''),
                        'source': 'edX'
                    })

                print(f"Fetched {len(courses)} edX courses so far...")

                page += 1
                time.sleep(0.5)  # Rate limiting

            except Exception as e:
                print(f"Error fetching edX courses: {e}")
                break

        print(f"\nTotal edX courses fetched: {len(courses)}")
        return courses

    def _map_edx_difficulty(self, level: str) -> str:
        """Map edX difficulty levels."""
        if not level:
            return 'Mixed'

        level = level.lower()
        if 'introductory' in level:
            return 'Beginner'
        elif 'intermediate' in level:
            return 'Intermediate'
        elif 'advanced' in level:
            return 'Advanced'
        return 'Mixed'

    # ==================== YOUTUBE API ====================

    def fetch_youtube_courses(
        self,
        search_query: str = "programming tutorial",
        max_courses: int = 50
    ) -> List[Dict]:
        """Fetch educational YouTube playlists.

        Requires YouTube Data API key:
        https://console.cloud.google.com/apis/credentials

        Args:
            search_query: Search term
            max_courses: Maximum playlists to fetch

        Returns:
            List of course dictionaries
        """
        if not self.youtube_api_key:
            print("\n[INFO] YouTube API not configured")
            print("\nTo use YouTube API:")
            print("1. Go to: https://console.cloud.google.com/apis/credentials")
            print("2. Create a new API key")
            print("3. Enable YouTube Data API v3")
            print("4. Add to .env file:")
            print("   YOUTUBE_API_KEY=your_api_key")
            return []

        print(f"Fetching YouTube courses for: {search_query}")

        courses = []
        url = "https://www.googleapis.com/youtube/v3/search"

        params = {
            'part': 'snippet',
            'q': f"{search_query} full course",
            'type': 'playlist',
            'maxResults': min(50, max_courses),
            'key': self.youtube_api_key,
            'order': 'relevance',
            'videoDuration': 'long'
        }

        try:
            response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                print(f"Error: {response.status_code} - {response.text}")
                return []

            data = response.json()

            for item in data.get('items', []):
                snippet = item.get('snippet', {})
                courses.append({
                    'course_name': snippet.get('title'),
                    'university': snippet.get('channelTitle', 'YouTube'),
                    'difficulty_level': 'Mixed',
                    'course_rating': None,
                    'course_url': f"https://www.youtube.com/playlist?list={item['id']['playlistId']}",
                    'course_description': snippet.get('description', ''),
                    'source': 'YouTube'
                })

            print(f"Fetched {len(courses)} YouTube playlists")

        except Exception as e:
            print(f"Error fetching YouTube courses: {e}")

        return courses

    # ==================== COMBINE & SAVE ====================

    def fetch_all_sources(
        self,
        udemy_query: str = "programming",
        edx_max: int = 100,
        youtube_query: str = "programming",
        udemy_max: int = 100
    ) -> pd.DataFrame:
        """Fetch courses from all available sources.

        Args:
            udemy_query: Search query for Udemy
            edx_max: Max edX courses
            youtube_query: Search query for YouTube
            udemy_max: Max Udemy courses

        Returns:
            Combined DataFrame with all courses
        """
        all_courses = []

        print("="*60)
        print("FETCHING COURSES FROM ALL SOURCES")
        print("="*60)

        # Fetch from Udemy
        print("\n1. UDEMY")
        print("-"*60)
        udemy_courses = self.fetch_udemy_courses(udemy_query, max_courses=udemy_max)
        all_courses.extend(udemy_courses)

        # Fetch from edX
        print("\n2. EDX")
        print("-"*60)
        edx_courses = self.fetch_edx_courses(max_courses=edx_max)
        all_courses.extend(edx_courses)

        # Fetch from YouTube
        print("\n3. YOUTUBE")
        print("-"*60)
        youtube_courses = self.fetch_youtube_courses(youtube_query)
        all_courses.extend(youtube_courses)

        # Convert to DataFrame
        if all_courses:
            df = pd.DataFrame(all_courses)

            # Save to CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"api_courses_{timestamp}.csv"
            df.to_csv(output_file, index=False)

            print("\n" + "="*60)
            print("SUMMARY")
            print("="*60)
            print(f"Total courses fetched: {len(df)}")
            print(f"Sources: {df['source'].value_counts().to_dict()}")
            print(f"Saved to: {output_file}")
            print("="*60)

            return df
        else:
            print("\n[WARNING] No courses fetched from any source")
            print("Please check your API credentials or internet connection")
            return pd.DataFrame()

    def save_courses(self, courses: List[Dict], filename: str = "fetched_courses.csv"):
        """Save courses to CSV.

        Args:
            courses: List of course dictionaries
            filename: Output filename
        """
        if not courses:
            print("No courses to save")
            return

        df = pd.DataFrame(courses)
        output_path = self.output_dir / filename

        df.to_csv(output_path, index=False)
        print(f"\nSaved {len(courses)} courses to: {output_path}")


def setup_instructions():
    """Print setup instructions for APIs."""
    print("\n" + "="*60)
    print("API SETUP INSTRUCTIONS")
    print("="*60)

    print("\n1. UDEMY API (Recommended - Easy to get)")
    print("-"*60)
    print("Steps:")
    print("  a. Sign up: https://www.udemy.com/affiliate/")
    print("  b. Get API credentials from affiliate dashboard")
    print("  c. Add to .env file:")
    print("     UDEMY_CLIENT_ID=your_client_id")
    print("     UDEMY_CLIENT_SECRET=your_client_secret")
    print("Benefits:")
    print("  + Free and easy to access")
    print("  + 100,000+ courses available")
    print("  + Detailed course information")

    print("\n2. EDX (No Auth Required)")
    print("-"*60)
    print("  + Works out of the box (no API key needed)")
    print("  + 3,000+ courses from top universities")
    print("  - No ratings available via API")

    print("\n3. YOUTUBE API (Optional)")
    print("-"*60)
    print("Steps:")
    print("  a. Go to: https://console.cloud.google.com/apis/credentials")
    print("  b. Create API key")
    print("  c. Enable YouTube Data API v3")
    print("  d. Add to .env:")
    print("     YOUTUBE_API_KEY=your_api_key")
    print("Benefits:")
    print("  + Free educational content")
    print("  + Full course playlists")

    print("\n4. COURSERA (Use Kaggle Dataset Instead)")
    print("-"*60)
    print("  - No public API available")
    print("  + Download dataset: https://www.kaggle.com/datasets/khusheekapoor/coursera-courses-dataset-2021")

    print("\n" + "="*60)
    print("RECOMMENDED SETUP:")
    print("="*60)
    print("1. Set up Udemy API (easiest, most courses)")
    print("2. Use edX (works immediately, no setup)")
    print("3. Optional: Add YouTube for free content")
    print("4. Optional: Download Coursera from Kaggle")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Show setup instructions
    setup_instructions()

    # Initialize collector
    collector = RealAPICollector()

    print("\nTesting available APIs...\n")

    # Try fetching from edX (no auth required)
    print("Testing edX (no auth required)...")
    edx_courses = collector.fetch_edx_courses(max_courses=10)

    if edx_courses:
        print(f"\n✅ edX works! Fetched {len(edx_courses)} courses")
        df = pd.DataFrame(edx_courses)
        print("\nSample courses:")
        print(df[['course_name', 'university']].head())
    else:
        print("\n❌ edX fetch failed")

    print("\n" + "="*60)
    print("To fetch from all sources, configure APIs and run:")
    print("="*60)
    print("from src.utils.real_api_collector import RealAPICollector")
    print("collector = RealAPICollector()")
    print("df = collector.fetch_all_sources()")
    print("="*60)
