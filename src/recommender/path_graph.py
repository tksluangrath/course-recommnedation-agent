"""
Learning Path Graph

Uses NetworkX to sequence courses within difficulty levels, estimate
learning timelines, and retrieve prerequisite chains from the DB.
"""

import sys
import os
from typing import Dict, List, Optional
from collections import defaultdict, deque

import networkx as nx
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'utils'))


class LearningPathGraph:
    """Handles prerequisite-aware sequencing and timeline estimation."""

    def __init__(self, db=None):
        """
        Args:
            db: DatabaseManager instance (optional). If None, imported lazily.
        """
        self._db = db

    def _get_db(self):
        if self._db is None:
            from database import DatabaseManager
            self._db = DatabaseManager()
        return self._db

    # ------------------------------------------------------------------
    # Intra-level sequencing
    # ------------------------------------------------------------------

    def sequence_within_level(self, courses_df: pd.DataFrame) -> pd.DataFrame:
        """Order courses so skill-teaching courses come before skill-using ones.

        Builds a directed graph where an edge A → B means "A teaches a skill
        that B also teaches, and A has a higher skill_match_ratio or lower
        difficulty sub-rank". Falls back to rating-based sort if the graph
        is trivial (no edges or all disconnected).

        Args:
            courses_df: DataFrame of courses at the same difficulty level.

        Returns:
            DataFrame with rows reordered by topological sort.
        """
        if len(courses_df) <= 1:
            return courses_df

        # Build skill sets per course
        skill_col = 'skills_list' if 'skills_list' in courses_df.columns else None
        if skill_col is None:
            # Try extracted_skills string
            if 'extracted_skills' in courses_df.columns:
                courses_df = courses_df.copy()
                courses_df['_skills'] = courses_df['extracted_skills'].apply(
                    lambda x: set(s.strip().lower() for s in str(x).split(',')) if pd.notna(x) else set()
                )
                skill_col = '_skills'

        G = nx.DiGraph()
        names = courses_df['course_name'].tolist()
        G.add_nodes_from(names)

        if skill_col:
            skill_map = {}
            for _, row in courses_df.iterrows():
                skills = row[skill_col]
                if isinstance(skills, list):
                    skill_map[row['course_name']] = set(s.lower() for s in skills)
                elif isinstance(skills, set):
                    skill_map[row['course_name']] = skills
                else:
                    skill_map[row['course_name']] = set()

            # Add edges: A → B if A has more unique skills relative to B
            # (i.e., A is more "foundational" in the context of this set)
            for i, a in enumerate(names):
                for j, b in enumerate(names):
                    if i == j:
                        continue
                    a_skills = skill_map.get(a, set())
                    b_skills = skill_map.get(b, set())
                    # A teaches skills B builds on: A's skills ⊂ B's skills
                    if a_skills and b_skills and a_skills < b_skills:
                        G.add_edge(a, b)

        # Topological sort if DAG, else fall back
        if nx.is_directed_acyclic_graph(G) and G.number_of_edges() > 0:
            try:
                order = list(nx.topological_sort(G))
                # Build index map for reordering
                order_map = {name: i for i, name in enumerate(order)}
                courses_df = courses_df.copy()
                courses_df['_topo_order'] = courses_df['course_name'].map(
                    lambda n: order_map.get(n, len(order))
                )
                courses_df = courses_df.sort_values('_topo_order').drop(columns=['_topo_order'])
                return courses_df.reset_index(drop=True)
            except Exception:
                pass

        # Fallback: sort by rating descending
        if 'course_rating' in courses_df.columns:
            return courses_df.sort_values('course_rating', ascending=False).reset_index(drop=True)
        return courses_df.reset_index(drop=True)

    # ------------------------------------------------------------------
    # Timeline estimation
    # ------------------------------------------------------------------

    def estimate_timeline(
        self,
        path: Dict[str, pd.DataFrame],
        hours_per_week: float = 10.0
    ) -> Dict:
        """Compute total hours and a week-by-week schedule for a learning path.

        Args:
            path: Dict mapping level name → DataFrame of courses.
            hours_per_week: Study hours available per week.

        Returns:
            {
                total_hours: float,
                weeks: float,
                per_level: {level: {count, hours}},
                schedule: [{weeks, level, courses}]
            }
        """
        level_order = ['Beginner', 'Intermediate', 'Advanced', 'Mixed']
        levels = [l for l in level_order if l in path] + [l for l in path if l not in level_order]

        per_level = {}
        for level in levels:
            df = path[level]
            if df is None or df.empty:
                continue
            if 'estimated_hours' in df.columns:
                hours = df['estimated_hours'].fillna(20.0).sum()
            else:
                hours = len(df) * 20.0  # default 20 hrs per course if unknown
            per_level[level] = {
                'count': len(df),
                'hours': round(hours, 1),
            }

        total_hours = sum(v['hours'] for v in per_level.values())
        weeks = total_hours / hours_per_week if hours_per_week > 0 else 0

        # Build schedule blocks
        schedule = []
        current_week = 1
        for level in levels:
            if level not in per_level:
                continue
            level_hours = per_level[level]['hours']
            level_weeks = max(1, round(level_hours / hours_per_week))
            end_week = current_week + level_weeks - 1
            df = path[level]
            schedule.append({
                'weeks': f"{current_week}–{end_week}",
                'level': level,
                'courses': df['course_name'].tolist() if 'course_name' in df.columns else [],
            })
            current_week = end_week + 1

        return {
            'total_hours': round(total_hours, 1),
            'weeks': round(weeks, 1),
            'hours_per_week': hours_per_week,
            'per_level': per_level,
            'schedule': schedule,
        }

    # ------------------------------------------------------------------
    # Prerequisite chain
    # ------------------------------------------------------------------

    def get_prerequisite_chain(self, course_name: str) -> List[str]:
        """Return an ordered prerequisite chain for a course using BFS.

        Traverses the `course_prerequisites` table backwards from the target
        course to find what must be completed first.

        Args:
            course_name: Name of the target course.

        Returns:
            Ordered list [earliest prerequisite, ..., target_course].
            Returns [course_name] if no prerequisites exist.
        """
        db = self._get_db()
        course = db.get_course_by_name(course_name)
        if not course:
            return [course_name]

        # BFS backwards through prerequisites
        visited = set()
        queue = deque([course.id])
        chain_ids = []

        while queue:
            cid = queue.popleft()
            if cid in visited:
                continue
            visited.add(cid)
            chain_ids.append(cid)
            prereqs = db.get_prerequisites(cid)
            for p in prereqs:
                if p.id not in visited:
                    queue.append(p.id)

        # Reverse so prerequisites come first
        chain_ids.reverse()

        # Resolve IDs to names
        result = []
        for cid in chain_ids:
            c = db.get_course_by_id(cid)
            if c:
                result.append(c.course_name)

        return result if result else [course_name]


if __name__ == "__main__":
    import torch  # Windows + Python 3.13 DLL workaround

    from database import DatabaseManager
    db = DatabaseManager()

    graph = LearningPathGraph(db=db)

    # Quick smoke test: prerequisite chain for a known course
    chain = graph.get_prerequisite_chain("Machine Learning")
    print("Prerequisite chain for 'Machine Learning':")
    for i, c in enumerate(chain):
        prefix = "  " * i + ("→ " if i > 0 else "")
        print(f"  {prefix}{c}")
