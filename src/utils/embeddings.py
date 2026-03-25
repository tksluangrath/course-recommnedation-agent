"""
Embeddings Manager for Course Recommendation System

Handles semantic search using sentence-transformers and ChromaDB.
Creates and manages vector embeddings for course descriptions.
"""

import os
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings


class EmbeddingManager:
    """Manages embeddings and semantic search for courses."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        chroma_path: str = "data/embeddings/chroma_db"
    ):
        """Initialize embedding manager.

        Args:
            model_name: Name of sentence-transformer model
            chroma_path: Path to ChromaDB storage
        """
        self.model_name = model_name
        self.chroma_path = Path(chroma_path)

        # Create directory
        self.chroma_path.mkdir(parents=True, exist_ok=True)

        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        print(f"Embedding dimension: {self.model.get_sentence_embedding_dimension()}")

        # Initialize ChromaDB
        print(f"Initializing ChromaDB at: {chroma_path}")
        self.client = chromadb.PersistentClient(path=str(self.chroma_path))

        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="courses",
            metadata={"description": "Course embeddings for semantic search"}
        )

        print(f"ChromaDB initialized. Current collection size: {self.collection.count()}")

    def create_embedding(self, text: str) -> np.ndarray:
        """Create embedding for a single text.

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding

    def create_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Create embeddings for multiple texts.

        Args:
            texts: List of input texts
            batch_size: Batch size for encoding

        Returns:
            Array of embeddings
        """
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        return embeddings

    def add_courses(self, courses_df: pd.DataFrame, text_column: str = "course_description"):
        """Add courses to the vector database.

        Args:
            courses_df: DataFrame with course data
            text_column: Column to use for embeddings
        """
        print(f"\nAdding {len(courses_df)} courses to vector database...")

        # Prepare texts for embedding
        texts = []
        ids = []
        metadatas = []

        for idx, row in courses_df.iterrows():
            # Create combined text for better semantic search
            course_name = row.get('course_name', '')
            description = row.get(text_column, '')
            category = row.get('category', '')

            # Combine for richer context
            combined_text = f"{course_name}. {description}"

            texts.append(combined_text)
            ids.append(f"course_{idx}")

            # Store metadata
            metadata = {
                'course_name': str(course_name),
                'difficulty': str(row.get('difficulty_level', 'Mixed')),
                'category': str(category),
                'rating': float(row.get('course_rating', 0.0)) if pd.notna(row.get('course_rating')) else 0.0,
                'university': str(row.get('university', '')),
            }
            metadatas.append(metadata)

        # Create embeddings
        print("Creating embeddings...")
        embeddings = self.create_embeddings_batch(texts)

        # Add to ChromaDB
        print("Storing in ChromaDB...")
        self.collection.add(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=metadatas
        )

        print(f"Successfully added {len(texts)} courses to vector database")
        print(f"Total courses in database: {self.collection.count()}")

    def search_courses(
        self,
        query: str,
        n_results: int = 10,
        difficulty: Optional[str] = None,
        category: Optional[str] = None,
        min_rating: Optional[float] = None
    ) -> pd.DataFrame:
        """Search for courses using semantic search.

        Args:
            query: Natural language search query
            n_results: Number of results to return
            difficulty: Filter by difficulty level
            category: Filter by category
            min_rating: Minimum rating filter

        Returns:
            DataFrame with search results
        """
        # Create query embedding
        query_embedding = self.create_embedding(query)

        # Build where filter
        where_filter = {}
        if difficulty:
            where_filter['difficulty'] = difficulty
        if category:
            where_filter['category'] = category

        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results * 2,  # Get more results to filter
            where=where_filter if where_filter else None
        )

        # Convert to DataFrame
        if not results['ids'] or len(results['ids'][0]) == 0:
            return pd.DataFrame()

        results_data = []
        for i in range(len(results['ids'][0])):
            metadata = results['metadatas'][0][i]

            # Apply rating filter
            if min_rating and metadata.get('rating', 0) < min_rating:
                continue

            results_data.append({
                'course_name': metadata.get('course_name'),
                'difficulty_level': metadata.get('difficulty'),
                'category': metadata.get('category'),
                'rating': metadata.get('rating'),
                'university': metadata.get('university'),
                'similarity_score': 1 - results['distances'][0][i],  # Convert distance to similarity
                'description': results['documents'][0][i]
            })

        df = pd.DataFrame(results_data)

        # Limit to n_results
        if len(df) > n_results:
            df = df.head(n_results)

        return df

    def find_similar_courses(
        self,
        course_name: str,
        n_results: int = 5
    ) -> pd.DataFrame:
        """Find courses similar to a given course.

        Args:
            course_name: Name of the course
            n_results: Number of similar courses to return

        Returns:
            DataFrame with similar courses
        """
        return self.search_courses(course_name, n_results=n_results)

    def clear_database(self):
        """Clear all embeddings from the database."""
        self.client.delete_collection("courses")
        self.collection = self.client.create_collection(
            name="courses",
            metadata={"description": "Course embeddings for semantic search"}
        )
        print("Database cleared")

    def get_stats(self) -> Dict:
        """Get statistics about the embedding database.

        Returns:
            Dictionary with statistics
        """
        count = self.collection.count()

        stats = {
            'total_courses': count,
            'model': self.model_name,
            'embedding_dimension': self.model.get_sentence_embedding_dimension(),
            'chroma_path': str(self.chroma_path)
        }

        return stats


def test_embeddings():
    """Test embeddings functionality."""
    print("="*60)
    print("TESTING EMBEDDINGS & SEMANTIC SEARCH")
    print("="*60)

    # Create sample courses
    sample_courses = pd.DataFrame({
        'course_name': [
            'Introduction to Machine Learning',
            'Deep Learning Specialization',
            'Python for Data Science',
            'Web Development with React',
            'Statistical Analysis with R',
            'Natural Language Processing',
            'Computer Vision Fundamentals'
        ],
        'course_description': [
            'Learn supervised and unsupervised machine learning algorithms including linear regression, logistic regression, and clustering.',
            'Master deep learning with neural networks, CNNs, RNNs, and transformers using TensorFlow and PyTorch.',
            'Complete Python programming course covering pandas, numpy, matplotlib, and data analysis techniques.',
            'Build modern web applications using React, JavaScript, HTML, and CSS. Includes hooks and state management.',
            'Learn statistical methods, hypothesis testing, and data analysis using the R programming language.',
            'Learn to process and analyze text data using transformers, word embeddings, and language models.',
            'Introduction to computer vision including image processing, object detection, and image classification.'
        ],
        'difficulty_level': ['Beginner', 'Advanced', 'Beginner', 'Intermediate', 'Intermediate', 'Advanced', 'Intermediate'],
        'category': ['Machine Learning', 'Machine Learning', 'Programming', 'Web Development', 'Data Science', 'Machine Learning', 'Machine Learning'],
        'course_rating': [4.5, 4.8, 4.3, 4.6, 4.4, 4.7, 4.5],
        'university': ['Stanford', 'DeepLearning.AI', 'Coursera', 'Meta', 'Duke', 'Stanford', 'MIT']
    })

    # Initialize manager
    em = EmbeddingManager()

    # Clear existing data
    em.clear_database()

    # Add courses
    em.add_courses(sample_courses)

    # Test searches
    print("\n" + "="*60)
    print("TEST 1: Search for 'machine learning for beginners'")
    print("="*60)
    results = em.search_courses("machine learning for beginners", n_results=3)
    print(results[['course_name', 'difficulty_level', 'similarity_score']])

    print("\n" + "="*60)
    print("TEST 2: Search for 'python programming' with difficulty filter")
    print("="*60)
    results = em.search_courses(
        "python programming",
        n_results=3,
        difficulty="Beginner"
    )
    print(results[['course_name', 'difficulty_level', 'similarity_score']])

    print("\n" + "="*60)
    print("TEST 3: Find courses similar to 'Deep Learning Specialization'")
    print("="*60)
    results = em.find_similar_courses("deep neural networks and transformers", n_results=3)
    print(results[['course_name', 'category', 'similarity_score']])

    print("\n" + "="*60)
    print("TEST 4: Database statistics")
    print("="*60)
    stats = em.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")

    print("\n" + "="*60)
    print("Embeddings test completed!")
    print("="*60)


if __name__ == "__main__":
    test_embeddings()
