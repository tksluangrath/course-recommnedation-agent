"""
Fetch real course data from Udemy API.

Prerequisites:
1. Join Udemy Affiliate Program: https://www.udemy.com/affiliate/
2. Get API credentials from affiliate dashboard
3. Add to .env file:
   UDEMY_CLIENT_ID=your_client_id
   UDEMY_CLIENT_SECRET=your_client_secret
"""

import os
import requests
import pandas as pd
from dotenv import load_dotenv
import time
from pathlib import Path

load_dotenv()


def fetch_udemy_courses(query="python", max_courses=500, language="en"):
    """Fetch courses from Udemy API.

    Args:
        query: Search term
        max_courses: Maximum number of courses to fetch
        language: Course language code (en, es, fr, etc.)

    Returns:
        List of course dictionaries
    """

    client_id = os.getenv("UDEMY_CLIENT_ID")
    client_secret = os.getenv("UDEMY_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("\n" + "="*60)
        print("ERROR: Udemy API credentials not found")
        print("="*60)
        print("\nTo use Udemy API:")
        print("1. Sign up for affiliate program: https://www.udemy.com/affiliate/")
        print("2. Get credentials from affiliate dashboard")
        print("3. Add to .env file:")
        print("   UDEMY_CLIENT_ID=your_client_id")
        print("   UDEMY_CLIENT_SECRET=your_client_secret")
        print("="*60 + "\n")
        return []

    courses = []
    page = 1

    print(f"\nFetching Udemy courses for: '{query}'")
    print("-" * 60)

    while len(courses) < max_courses:
        url = "https://www.udemy.com/api-2.0/courses/"

        params = {
            'search': query,
            'page': page,
            'page_size': min(100, max_courses - len(courses)),
            'language': language,
            'ordering': 'most-reviewed'
        }

        try:
            response = requests.get(
                url,
                auth=(client_id, client_secret),
                params=params,
                timeout=10
            )

            if response.status_code != 200:
                print(f"\nError {response.status_code}: {response.text}")
                break

            data = response.json()

            if not data.get('results'):
                print(f"\nNo more results found")
                break

            for course in data['results']:
                # Map difficulty level
                difficulty = course.get('instructional_level', 'all')
                if difficulty == 'all':
                    difficulty = 'Beginner'
                elif difficulty == 'intermediate':
                    difficulty = 'Intermediate'
                elif difficulty == 'expert':
                    difficulty = 'Advanced'

                courses.append({
                    'Course Name': course.get('title'),
                    'University': 'Udemy',
                    'Difficulty Level': difficulty,
                    'Course Rating': course.get('rating'),
                    'Course Description': course.get('headline', ''),
                    'Course URL': f"https://www.udemy.com{course.get('url', '')}",
                    'Price': course.get('price'),
                    'Num Reviews': course.get('num_reviews'),
                    'Num Subscribers': course.get('num_subscribers'),
                })

            print(f"Fetched {len(courses)} courses so far...", end='\r')

            # Check if there are more pages
            if not data.get('next'):
                break

            page += 1
            time.sleep(0.3)  # Rate limiting

        except Exception as e:
            print(f"\nError fetching data: {e}")
            break

    print(f"\nTotal courses fetched: {len(courses)}")
    return courses


def fetch_multiple_topics(topics=None, courses_per_topic=100):
    """Fetch courses for multiple topics.

    Args:
        topics: List of search queries
        courses_per_topic: Max courses per topic

    Returns:
        DataFrame with all courses
    """
    if topics is None:
        topics = [
            'python programming',
            'machine learning',
            'web development',
            'data science',
            'javascript',
            'data analysis',
            'artificial intelligence',
            'cybersecurity'
        ]

    all_courses = []

    print("="*60)
    print("FETCHING UDEMY COURSES")
    print("="*60)

    for topic in topics:
        courses = fetch_udemy_courses(topic, max_courses=courses_per_topic)
        all_courses.extend(courses)
        print("")

    if not all_courses:
        print("\nNo courses fetched. Check your API credentials.")
        return pd.DataFrame()

    # Convert to DataFrame and remove duplicates
    df = pd.DataFrame(all_courses)

    # Remove duplicates based on course name
    original_count = len(df)
    df = df.drop_duplicates(subset=['Course Name'])
    duplicates_removed = original_count - len(df)

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total courses fetched: {original_count}")
    print(f"Duplicates removed: {duplicates_removed}")
    print(f"Unique courses: {len(df)}")
    print(f"Average rating: {df['Course Rating'].mean():.2f}")
    print("\nDifficulty distribution:")
    print(df['Difficulty Level'].value_counts())
    print("="*60)

    return df


def main():
    """Main function to fetch and save Udemy courses."""

    # Create output directory
    output_dir = Path('data/raw')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch courses
    df = fetch_multiple_topics(
        topics=[
            'python',
            'machine learning',
            'web development',
            'data science',
            'javascript',
            'sql',
            'react',
            'artificial intelligence'
        ],
        courses_per_topic=50  # Fetch 50 courses per topic
    )

    if df.empty:
        print("\nNo data to save. Exiting.")
        return

    # Save to CSV
    output_file = output_dir / 'udemy_courses.csv'
    df.to_csv(output_file, index=False)

    print(f"\nSaved {len(df)} courses to: {output_file}")

    # Show sample
    print("\nSample courses:")
    print(df[['Course Name', 'Difficulty Level', 'Course Rating']].head(10))

    print("\n" + "="*60)
    print("Udemy data fetch completed!")
    print("="*60)


if __name__ == "__main__":
    main()
