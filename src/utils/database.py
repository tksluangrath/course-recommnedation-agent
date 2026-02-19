"""
Database Manager for Course Recommendation System

Handles SQLite database operations for storing course data,
user interactions, and recommendations.
"""

import os
import json
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
    Table,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

# Association table for many-to-many relationship (courses and skills)
course_skills = Table(
    'course_skills',
    Base.metadata,
    Column('course_id', Integer, ForeignKey('courses.id')),
    Column('skill_id', Integer, ForeignKey('skills.id'))
)

# Association table for prerequisites
course_prerequisites = Table(
    'course_prerequisites',
    Base.metadata,
    Column('course_id', Integer, ForeignKey('courses.id')),
    Column('prerequisite_id', Integer, ForeignKey('courses.id'))
)


class Course(Base):
    """Course model - stores course metadata."""
    __tablename__ = 'courses'

    id = Column(Integer, primary_key=True)
    course_name = Column(String, nullable=False, index=True)
    university = Column(String, index=True)
    difficulty_level = Column(String, index=True)  # Beginner, Intermediate, Advanced
    course_rating = Column(Float)
    course_url = Column(String)
    course_description = Column(Text)

    # Extracted features
    category = Column(String, index=True)
    estimated_hours = Column(Float)
    num_reviews = Column(Integer)
    learning_product = Column(String)  # Course, Specialization, Guided Project, etc.

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    skills = relationship('Skill', secondary=course_skills, back_populates='courses')
    prerequisites = relationship(
        'Course',
        secondary=course_prerequisites,
        primaryjoin=id == course_prerequisites.c.course_id,
        secondaryjoin=id == course_prerequisites.c.prerequisite_id,
        backref='required_for'
    )

    def __repr__(self):
        return f"<Course(id={self.id}, name='{self.course_name}', difficulty='{self.difficulty_level}')>"


class Skill(Base):
    """Skill model - stores skills extracted from courses."""
    __tablename__ = 'skills'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False, index=True)

    # Relationships
    courses = relationship('Course', secondary=course_skills, back_populates='skills')

    def __repr__(self):
        return f"<Skill(id={self.id}, name='{self.name}')>"


class UserProfile(Base):
    """User profile model — persists across sessions."""
    __tablename__ = 'user_profiles'

    user_id = Column(String, primary_key=True)
    known_skills = Column(Text, default='[]')       # JSON array: '["Python","SQL"]'
    goals = Column(Text, default='')                # free-text learning goal
    hours_per_week = Column(Float, default=10.0)
    preferred_difficulty = Column(String, default=None)  # Beginner/Intermediate/Advanced
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UserProfile(user_id='{self.user_id}', goals='{self.goals[:30]}')>"


class UserInteraction(Base):
    """User interaction model - for collaborative filtering."""
    __tablename__ = 'user_interactions'

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    interaction_type = Column(String)  # viewed, enrolled, completed, rated
    rating = Column(Float)  # Optional rating (1-5)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<UserInteraction(user={self.user_id}, course={self.course_id}, type='{self.interaction_type}')>"


class DatabaseManager:
    """Manages database connections and operations."""

    def __init__(self, db_path: str = "data/courses.db"):
        """Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Create engine and session
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.Session = sessionmaker(bind=self.engine)

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)

        print(f"Database initialized at: {db_path}")

    def add_course(self, course_data: Dict) -> Course:
        """Add a single course to the database.

        Args:
            course_data: Dictionary with course information

        Returns:
            Created Course object
        """
        session = self.Session()
        try:
            # Check if course already exists (by name and university)
            existing = session.query(Course).filter_by(
                course_name=course_data['course_name'],
                university=course_data.get('university')
            ).first()

            if existing:
                print(f"Course already exists: {course_data['course_name']}")
                return existing

            # Create new course
            course = Course(**course_data)
            session.add(course)
            session.commit()
            session.refresh(course)

            return course

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def add_courses_batch(self, courses_data: List[Dict]) -> int:
        """Add multiple courses in a batch.

        Args:
            courses_data: List of course dictionaries

        Returns:
            Number of courses added
        """
        session = self.Session()
        count = 0

        try:
            for course_data in courses_data:
                # Check if exists
                existing = session.query(Course).filter_by(
                    course_name=course_data['course_name'],
                    university=course_data.get('university')
                ).first()

                if not existing:
                    course = Course(**course_data)
                    session.add(course)
                    count += 1

            session.commit()
            print(f"Added {count} courses to database")
            return count

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def search_courses(
        self,
        query: Optional[str] = None,
        difficulty: Optional[str] = None,
        category: Optional[str] = None,
        min_rating: Optional[float] = None,
        limit: int = 10
    ) -> List[Course]:
        """Search courses by various criteria.

        Args:
            query: Text search in name/description
            difficulty: Filter by difficulty level
            category: Filter by category
            min_rating: Minimum rating
            limit: Maximum results

        Returns:
            List of Course objects
        """
        session = self.Session()
        try:
            q = session.query(Course)

            if query:
                q = q.filter(
                    Course.course_name.contains(query) |
                    Course.course_description.contains(query)
                )

            if difficulty:
                q = q.filter(Course.difficulty_level == difficulty)

            if category:
                q = q.filter(Course.category == category)

            if min_rating:
                q = q.filter(Course.course_rating >= min_rating)

            results = q.limit(limit).all()
            return results

        finally:
            session.close()

    def get_course_by_id(self, course_id: int) -> Optional[Course]:
        """Get a course by ID.

        Args:
            course_id: Course ID

        Returns:
            Course object or None
        """
        session = self.Session()
        try:
            return session.query(Course).filter(Course.id == course_id).first()
        finally:
            session.close()

    def get_all_courses(self) -> List[Course]:
        """Get all courses from database.

        Returns:
            List of all Course objects
        """
        session = self.Session()
        try:
            return session.query(Course).all()
        finally:
            session.close()

    def add_skill(self, skill_name: str) -> Skill:
        """Add a skill to the database.

        Args:
            skill_name: Name of the skill

        Returns:
            Skill object
        """
        session = self.Session()
        try:
            # Check if exists
            existing = session.query(Skill).filter_by(name=skill_name).first()
            if existing:
                return existing

            skill = Skill(name=skill_name)
            session.add(skill)
            session.commit()
            session.refresh(skill)
            return skill

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def link_course_skill(self, course_id: int, skill_name: str):
        """Link a course with a skill.

        Args:
            course_id: Course ID
            skill_name: Skill name
        """
        session = self.Session()
        try:
            course = session.query(Course).filter(Course.id == course_id).first()
            if not course:
                raise ValueError(f"Course {course_id} not found")

            # Get or create skill
            skill = session.query(Skill).filter_by(name=skill_name).first()
            if not skill:
                skill = Skill(name=skill_name)
                session.add(skill)

            # Add to relationship if not already linked
            if skill not in course.skills:
                course.skills.append(skill)

            session.commit()

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    # ------------------------------------------------------------------
    # User profile methods
    # ------------------------------------------------------------------

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get a user profile by user_id, or None if not found."""
        session = self.Session()
        try:
            return session.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        finally:
            session.close()

    def get_or_create_profile(self, user_id: str) -> dict:
        """Load an existing profile or create a blank one. Returns dict with deserialized fields."""
        session = self.Session()
        try:
            profile = session.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if not profile:
                profile = UserProfile(user_id=user_id)
                session.add(profile)
                session.commit()
            return {
                'user_id': profile.user_id,
                'known_skills': json.loads(profile.known_skills or '[]'),
                'goals': profile.goals or '',
                'hours_per_week': profile.hours_per_week or 10.0,
                'preferred_difficulty': profile.preferred_difficulty,
            }
        finally:
            session.close()

    def update_profile(self, user_id: str, **kwargs) -> dict:
        """Update profile fields. Accepts known_skills as List[str] (auto-serialized).

        Returns updated profile as dict.
        """
        session = self.Session()
        try:
            profile = session.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if not profile:
                profile = UserProfile(user_id=user_id)
                session.add(profile)

            for key, value in kwargs.items():
                if key == 'known_skills' and isinstance(value, list):
                    value = json.dumps(value)
                if hasattr(profile, key):
                    setattr(profile, key, value)

            session.commit()
            return {
                'user_id': profile.user_id,
                'known_skills': json.loads(profile.known_skills or '[]'),
                'goals': profile.goals or '',
                'hours_per_week': profile.hours_per_week or 10.0,
                'preferred_difficulty': profile.preferred_difficulty,
            }
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Course prerequisite methods
    # ------------------------------------------------------------------

    def get_course_by_name(self, course_name: str) -> Optional[Course]:
        """Get a course by exact or partial name match."""
        session = self.Session()
        try:
            course = session.query(Course).filter(
                Course.course_name == course_name
            ).first()
            if not course:
                course = session.query(Course).filter(
                    Course.course_name.contains(course_name)
                ).first()
            return course
        finally:
            session.close()

    def add_prerequisite(self, course_id: int, prereq_id: int):
        """Add a prerequisite relationship between two courses."""
        session = self.Session()
        try:
            course = session.query(Course).filter(Course.id == course_id).first()
            prereq = session.query(Course).filter(Course.id == prereq_id).first()
            if not course or not prereq:
                return
            if prereq not in course.prerequisites:
                course.prerequisites.append(prereq)
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_prerequisites(self, course_id: int) -> List[Course]:
        """Get all prerequisite courses for a given course."""
        session = self.Session()
        try:
            course = session.query(Course).filter(Course.id == course_id).first()
            if not course:
                return []
            prereqs = list(course.prerequisites)
            return prereqs
        finally:
            session.close()

    def populate_prerequisites_heuristic(self, min_shared_skills: int = 2) -> int:
        """Heuristically seed the course_prerequisites table.

        For each pair (A, B) in the same category where A.difficulty < B.difficulty
        and they share >= min_shared_skills skills, A is a prerequisite for B.

        Difficulty order: Beginner=0, Mixed=1, Intermediate=1, Advanced=2
        Caps prerequisites per course at 3 to keep the graph sparse.

        Returns:
            Number of prerequisite relationships inserted.
        """
        DIFF_ORDER = {'Beginner': 0, 'Mixed': 1, 'Intermediate': 1, 'Advanced': 2}

        session = self.Session()
        try:
            # Load all courses with their skill names grouped by category
            courses = session.query(Course).all()

            # Build in-memory index: {category: [course_info]}
            from collections import defaultdict
            cat_courses = defaultdict(list)
            for c in courses:
                skill_names = {s.name for s in c.skills}
                cat_courses[c.category].append({
                    'id': c.id,
                    'diff': DIFF_ORDER.get(c.difficulty_level, 1),
                    'skills': skill_names,
                    'prereq_count': 0,
                })

            inserted = 0
            prereq_counts = defaultdict(int)  # course_id -> how many prereqs it has

            for category, course_list in cat_courses.items():
                if len(course_list) < 2:
                    continue
                # Sort by difficulty ascending
                course_list.sort(key=lambda x: x['diff'])

                for i, harder in enumerate(course_list):
                    for easier in course_list[:i]:
                        # Only connect across different difficulty tiers
                        if easier['diff'] >= harder['diff']:
                            continue
                        # Check shared skills
                        shared = easier['skills'] & harder['skills']
                        if len(shared) < min_shared_skills:
                            continue
                        # Cap prerequisites per course at 3
                        if prereq_counts[harder['id']] >= 3:
                            continue

                        # Check if already exists
                        harder_course = session.query(Course).filter(Course.id == harder['id']).first()
                        easier_course = session.query(Course).filter(Course.id == easier['id']).first()
                        if easier_course not in harder_course.prerequisites:
                            harder_course.prerequisites.append(easier_course)
                            prereq_counts[harder['id']] += 1
                            inserted += 1

            session.commit()
            return inserted

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_stats(self) -> Dict:
        """Get database statistics.

        Returns:
            Dictionary with stats
        """
        session = self.Session()
        try:
            stats = {
                'total_courses': session.query(Course).count(),
                'total_skills': session.query(Skill).count(),
                'total_interactions': session.query(UserInteraction).count(),
                'difficulty_distribution': {}
            }

            # Count by difficulty
            for difficulty in ['Beginner', 'Intermediate', 'Advanced', 'Mixed']:
                count = session.query(Course).filter(
                    Course.difficulty_level == difficulty
                ).count()
                stats['difficulty_distribution'][difficulty] = count

            return stats

        finally:
            session.close()


def test_database():
    """Test database functionality."""
    print("="*60)
    print("TESTING DATABASE")
    print("="*60)

    # Initialize database
    db = DatabaseManager()

    # Test: Add a sample course
    print("\n1. Adding a test course...")
    sample_course = {
        'course_name': 'Introduction to Machine Learning',
        'university': 'Stanford University',
        'difficulty_level': 'Intermediate',
        'course_rating': 4.8,
        'course_url': 'https://example.com/ml-course',
        'course_description': 'Learn the fundamentals of machine learning, including supervised and unsupervised learning.',
        'category': 'Machine Learning',
        'estimated_hours': 40.0
    }

    course = db.add_course(sample_course)
    print(f"Added course: {course}")

    # Test: Add skills
    print("\n2. Adding skills to course...")
    db.link_course_skill(course.id, 'Python')
    db.link_course_skill(course.id, 'Machine Learning')
    db.link_course_skill(course.id, 'Statistics')
    print("Skills linked successfully")

    # Test: Search
    print("\n3. Searching for courses...")
    results = db.search_courses(query='machine learning', limit=5)
    print(f"Found {len(results)} courses")
    for c in results:
        print(f"  - {c.course_name} ({c.difficulty_level})")

    # Test: Get stats
    print("\n4. Database statistics:")
    stats = db.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n" + "="*60)
    print("Database test completed!")
    print("="*60)


if __name__ == "__main__":
    test_database()
