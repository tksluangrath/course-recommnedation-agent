"""
API Collectors for Course Data

Provides two collectors for fetching live course data:
- CourseraAPI: Fetches from Coursera Catalog API (OAuth2 client credentials)
- RealAPICollector: Fetches from edX (no auth) and YouTube API
"""

import os
import sys
import time
import requests
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()


# ===========================================================================
# Coursera API (OAuth2)
# ===========================================================================

class CourseraAPI:
    """Coursera API client using OAuth2 client credentials flow."""

    TOKEN_URL = "https://api.coursera.com/oauth2/client_credentials/token"
    BASE_URL = "https://api.coursera.org/api"

    def __init__(self):
        self.client_id = os.getenv("COURSERA_CLIENT_ID", "")
        self.client_secret = os.getenv("COURSERA_CLIENT_SECRET", "")
        self.access_token = None
        self.token_expiry = 0

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def authenticate(self) -> bool:
        """Get access token using OAuth2 client credentials flow."""
        if not self.is_configured():
            print("[ERROR] Coursera API credentials not found in .env")
            print("  Add COURSERA_CLIENT_ID and COURSERA_CLIENT_SECRET to .env")
            return False

        try:
            response = requests.post(self.TOKEN_URL, data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials"
            })

            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                self.token_expiry = time.time() + data.get("expires_in", 1800)
                print("[OK] Authenticated with Coursera API")
                return True
            else:
                print(f"[ERROR] Authentication failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return False

        except Exception as e:
            print(f"[ERROR] Authentication error: {e}")
            return False

    def _get_headers(self) -> Dict:
        if time.time() >= self.token_expiry:
            self.authenticate()
        return {"Authorization": f"Bearer {self.access_token}"}

    def _api_get(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make authenticated GET request to Coursera API."""
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = requests.get(url, headers=self._get_headers(), params=params)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[WARN] API request failed: {response.status_code} - {endpoint}")
                return None
        except Exception as e:
            print(f"[ERROR] API request error: {e}")
            return None

    def fetch_courses(self, limit: int = 100, start: int = 0,
                      fields: str = None) -> Optional[Dict]:
        """Fetch courses from the catalog API."""
        if fields is None:
            fields = "name,slug,description,workload,courseType,primaryLanguages,subtitleLanguages"

        params = {
            "start": start,
            "limit": min(limit, 100),
            "fields": fields,
            "includes": "partnerIds"
        }
        return self._api_get("courses.v1", params)

    def fetch_all_courses(self, max_courses: int = 5000) -> pd.DataFrame:
        """Fetch all available courses with pagination."""
        if not self.authenticate():
            return pd.DataFrame()

        all_courses = []
        start = 0
        page_size = 100

        print(f"\nFetching courses (max {max_courses})...")

        while start < max_courses:
            data = self.fetch_courses(limit=page_size, start=start)
            if not data or "elements" not in data:
                break

            elements = data["elements"]
            if not elements:
                break

            all_courses.extend(elements)
            start += len(elements)
            print(f"  Fetched {len(all_courses)} courses...")

            paging = data.get("paging", {})
            total = paging.get("total", 0)
            if start >= total:
                break

            time.sleep(0.5)

        if not all_courses:
            print("[WARN] No courses fetched from API")
            return pd.DataFrame()

        print(f"\nTotal courses fetched: {len(all_courses)}")
        return self._parse_courses(all_courses)

    def _parse_courses(self, courses: List[Dict]) -> pd.DataFrame:
        """Parse raw API course data into a standardized DataFrame."""
        parsed = []
        for course in courses:
            parsed.append({
                "course_name": course.get("name", ""),
                "slug": course.get("slug", ""),
                "course_description": course.get("description", ""),
                "workload": course.get("workload", ""),
                "course_type": course.get("courseType", ""),
                "primary_languages": ", ".join(course.get("primaryLanguages", [])),
                "coursera_id": course.get("id", ""),
                "course_url": f"https://www.coursera.org/learn/{course.get('slug', '')}",
                "source": "coursera_api"
            })
        return pd.DataFrame(parsed)

    def fetch_partners(self) -> pd.DataFrame:
        """Fetch partner/university information."""
        if not self.access_token:
            if not self.authenticate():
                return pd.DataFrame()

        data = self._api_get("partners.v1", {
            "limit": 100,
            "fields": "name,shortName,description,homeLink,location"
        })

        if not data or "elements" not in data:
            return pd.DataFrame()

        partners = []
        for p in data["elements"]:
            partners.append({
                "partner_id": p.get("id", ""),
                "name": p.get("name", ""),
                "short_name": p.get("shortName", ""),
                "home_link": p.get("homeLink", ""),
            })

        return pd.DataFrame(partners)

    def fetch_and_save(self, output_path: str = "data/raw/coursera_api.csv",
                       max_courses: int = 5000) -> pd.DataFrame:
        """Fetch courses and save to CSV."""
        print("=" * 60)
        print("FETCHING COURSES FROM COURSERA API")
        print("=" * 60)

        df = self.fetch_all_courses(max_courses=max_courses)

        if df.empty:
            print("\n[ERROR] No courses fetched")
            return df

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output, index=False)
        print(f"\nSaved {len(df)} courses to: {output}")

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total courses: {len(df)}")
        print(f"With descriptions: {df['course_description'].notna().sum()}")
        print(f"Course types: {df['course_type'].value_counts().to_dict()}")
        print("=" * 60)

        return df

    def merge_with_kaggle(self, kaggle_path: str = "data/raw/coursera.csv",
                          api_path: str = "data/raw/coursera_api.csv",
                          output_path: str = "data/raw/coursera_merged.csv") -> pd.DataFrame:
        """Merge API data with existing Kaggle dataset."""
        print("\n" + "=" * 60)
        print("MERGING KAGGLE + API DATA")
        print("=" * 60)

        kaggle_df = pd.DataFrame()
        api_df = pd.DataFrame()

        if Path(kaggle_path).exists():
            kaggle_df = pd.read_csv(kaggle_path)
            print(f"Kaggle dataset: {len(kaggle_df)} courses")

        if Path(api_path).exists():
            api_df = pd.read_csv(api_path)
            print(f"API dataset: {len(api_df)} courses")

        if kaggle_df.empty and api_df.empty:
            print("[ERROR] No data to merge")
            return pd.DataFrame()

        if kaggle_df.empty:
            merged = api_df
        elif api_df.empty:
            merged = kaggle_df
        else:
            kaggle_names = set(kaggle_df.get("Title", kaggle_df.get("course_name", pd.Series())).str.lower())
            api_names = set(api_df["course_name"].str.lower())

            overlap = kaggle_names & api_names
            only_api = api_names - kaggle_names

            print(f"\nOverlapping courses: {len(overlap)}")
            print(f"API-only courses: {len(only_api)}")

            api_only_df = api_df[api_df["course_name"].str.lower().isin(only_api)]
            merged = pd.concat([kaggle_df, api_only_df], ignore_index=True)

        merged.to_csv(output_path, index=False)
        print(f"\nMerged dataset: {len(merged)} courses -> {output_path}")
        print("=" * 60)

        return merged


# ===========================================================================
# edX + YouTube Collector
# ===========================================================================

class RealAPICollector:
    """Fetches real course data from edX (no auth) and YouTube API."""

    def __init__(self, output_dir: str = "data/raw"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY", "")

    def fetch_edx_courses(self, max_courses: int = 100) -> List[Dict]:
        """Fetch edX courses using their public search API (no auth required)."""
        print("Fetching edX courses...")

        courses = []
        page = 0
        page_size = 50

        while len(courses) < max_courses:
            url = "https://www.edx.org/api/v1/catalog/search"
            params = {'page': page, 'page_size': page_size, 'content_type': 'course'}

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
                        'course_rating': None,
                        'course_url': f"https://www.edx.org{course.get('marketing_url', '')}",
                        'course_description': course.get('short_description', ''),
                        'source': 'edX'
                    })

                print(f"Fetched {len(courses)} edX courses so far...")
                page += 1
                time.sleep(0.5)

            except Exception as e:
                print(f"Error fetching edX courses: {e}")
                break

        print(f"\nTotal edX courses fetched: {len(courses)}")
        return courses

    def _map_edx_difficulty(self, level: str) -> str:
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

    def fetch_youtube_courses(self, search_query: str = "programming tutorial",
                              max_courses: int = 50) -> List[Dict]:
        """Fetch educational YouTube playlists (requires YOUTUBE_API_KEY in .env)."""
        if not self.youtube_api_key:
            print("\n[INFO] YouTube API not configured — add YOUTUBE_API_KEY to .env")
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

    def fetch_all_sources(self, edx_max: int = 100,
                          youtube_query: str = "programming") -> pd.DataFrame:
        """Fetch courses from edX and YouTube, save combined CSV."""
        all_courses = []

        print("="*60)
        print("FETCHING COURSES FROM ALL SOURCES")
        print("="*60)

        print("\n1. EDX")
        print("-"*60)
        all_courses.extend(self.fetch_edx_courses(max_courses=edx_max))

        print("\n2. YOUTUBE")
        print("-"*60)
        all_courses.extend(self.fetch_youtube_courses(youtube_query))

        if all_courses:
            df = pd.DataFrame(all_courses)
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
            return pd.DataFrame()

    def save_courses(self, courses: List[Dict], filename: str = "fetched_courses.csv"):
        """Save a list of course dicts to CSV."""
        if not courses:
            print("No courses to save")
            return
        df = pd.DataFrame(courses)
        output_path = self.output_dir / filename
        df.to_csv(output_path, index=False)
        print(f"\nSaved {len(courses)} courses to: {output_path}")


# ===========================================================================
# Setup instructions
# ===========================================================================

def setup_instructions():
    """Print setup instructions for all supported APIs."""
    print("\n" + "="*60)
    print("API SETUP INSTRUCTIONS")
    print("="*60)

    print("\n1. COURSERA KAGGLE DATASET (Recommended — no credentials needed)")
    print("-"*60)
    print("  Download: https://www.kaggle.com/datasets/yosefxx590/coursera-courses-and-skills-dataset-2025")
    print("  Place in: data/raw/coursera_courses_2025.csv")
    print("  Then run: python src/utils/data_cleaner.py")

    print("\n2. COURSERA API (OAuth2 — optional)")
    print("-"*60)
    print("  a. Register at: https://www.coursera.org/about/programs/api")
    print("  b. Add to .env:")
    print("     COURSERA_CLIENT_ID=your_id")
    print("     COURSERA_CLIENT_SECRET=your_secret")
    print("  c. Run: python src/utils/api_collectors.py")

    print("\n3. EDX (No auth required)")
    print("-"*60)
    print("  Works out of the box — 3,000+ courses from top universities")
    print("  Run: RealAPICollector().fetch_edx_courses()")

    print("\n4. YOUTUBE API (Optional)")
    print("-"*60)
    print("  a. Go to: https://console.cloud.google.com/apis/credentials")
    print("  b. Create API key, enable YouTube Data API v3")
    print("  c. Add to .env: YOUTUBE_API_KEY=your_api_key")

    print("\n" + "="*60)


if __name__ == "__main__":
    setup_instructions()

    # Demo: test Coursera API if configured
    api = CourseraAPI()
    if api.is_configured():
        df = api.fetch_and_save()
        if not df.empty and Path("data/raw/coursera.csv").exists():
            api.merge_with_kaggle()
    else:
        print("\nCoursera API not configured — testing edX instead...")
        collector = RealAPICollector()
        edx = collector.fetch_edx_courses(max_courses=10)
        if edx:
            print(f"\nedX works! Sample: {edx[0]['course_name']}")
