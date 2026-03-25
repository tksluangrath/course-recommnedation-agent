"""
Fetch Coursera 2025 Dataset from Kaggle

Downloads the Coursera Courses and Skills dataset (2025)
and saves it to data/raw/ for processing.

Prerequisites:
    pip install kagglehub[pandas-datasets]
"""

import os
from pathlib import Path

import kagglehub
import pandas as pd


def fetch_coursera_2025():
    """Download and save Coursera 2025 dataset."""

    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "coursera.csv"

    print("=" * 60)
    print("FETCHING COURSERA 2025 DATASET")
    print("=" * 60)

    # Download dataset files from Kaggle
    print("\nDownloading from Kaggle...")
    dataset_path = kagglehub.dataset_download(
        "yosefxx590/coursera-courses-and-skills-dataset-2025"
    )
    print(f"Downloaded to: {dataset_path}")

    # Load the CSV file
    csv_path = Path(dataset_path) / "Coursera.csv"
    df = pd.read_csv(csv_path)

    print(f"\nDataset loaded: {len(df)} courses")
    print(f"Columns: {df.columns.tolist()}")

    # Preview
    print("\nFirst 5 records:")
    print(df.head())

    # Save to CSV
    df.to_csv(output_file, index=False)
    print(f"\nSaved to: {output_file}")

    # Summary stats
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total courses: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    for col in df.columns:
        non_null = df[col].notna().sum()
        print(f"  {col}: {non_null} non-null values")

    print("=" * 60)
    return df


if __name__ == "__main__":
    fetch_coursera_2025()
