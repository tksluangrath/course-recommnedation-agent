"""
Coursera API Collector

Fetches course data from the Coursera Catalog API using OAuth2 client credentials.
Supplements the Kaggle dataset with live API data including descriptions,
partner info, and course metadata.
"""

import os
import sys
import time
import requests
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List
from dotenv import load_dotenv

load_dotenv()


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
        """Fetch courses from the catalog API.

        Args:
            limit: Number of courses per page (max 100)
            start: Pagination offset
            fields: Comma-separated fields to include
        """
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
        """Fetch all available courses with pagination.

        Args:
            max_courses: Maximum number of courses to fetch

        Returns:
            DataFrame with course data
        """
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

            # Check if there are more pages
            paging = data.get("paging", {})
            total = paging.get("total", 0)
            if start >= total:
                break

            # Rate limiting
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
        """Fetch courses and save to CSV.

        Args:
            output_path: Path to save the CSV
            max_courses: Maximum courses to fetch

        Returns:
            DataFrame with fetched courses
        """
        print("=" * 60)
        print("FETCHING COURSES FROM COURSERA API")
        print("=" * 60)

        df = self.fetch_all_courses(max_courses=max_courses)

        if df.empty:
            print("\n[ERROR] No courses fetched")
            return df

        # Save to CSV
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output, index=False)
        print(f"\nSaved {len(df)} courses to: {output}")

        # Summary
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
        """Merge API data with existing Kaggle dataset.

        Deduplicates by course name, preferring API data when available
        (since it may have descriptions the Kaggle data lacks).

        Args:
            kaggle_path: Path to Kaggle CSV
            api_path: Path to API CSV
            output_path: Path to save merged CSV
        """
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
            # Normalize names for deduplication
            kaggle_names = set(kaggle_df.get("Title", kaggle_df.get("course_name", pd.Series())).str.lower())
            api_names = set(api_df["course_name"].str.lower())

            overlap = kaggle_names & api_names
            only_api = api_names - kaggle_names

            print(f"\nOverlapping courses: {len(overlap)}")
            print(f"API-only courses: {len(only_api)}")

            # Keep all Kaggle data + API-only courses
            api_only_df = api_df[api_df["course_name"].str.lower().isin(only_api)]
            merged = pd.concat([kaggle_df, api_only_df], ignore_index=True)

        merged.to_csv(output_path, index=False)
        print(f"\nMerged dataset: {len(merged)} courses -> {output_path}")
        print("=" * 60)

        return merged


if __name__ == "__main__":
    api = CourseraAPI()

    if not api.is_configured():
        print("Coursera API credentials not found.")
        print("Add to .env: COURSERA_CLIENT_ID and COURSERA_CLIENT_SECRET")
        sys.exit(1)

    # Fetch and save courses
    df = api.fetch_and_save()

    # Optionally merge with Kaggle data
    if not df.empty and Path("data/raw/coursera.csv").exists():
        api.merge_with_kaggle()
