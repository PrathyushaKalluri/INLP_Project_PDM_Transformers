"""Remove duplicate tasks using semantic similarity."""

import os
from typing import List, Dict, Optional

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"


class Deduplicator:
    """
    Remove semantic duplicate or near-duplicate tasks.
    
    Uses semantic embeddings (cosine similarity) to detect and merge
    redundant tasks. This catches tasks that are semantically equivalent
    even if not identical in wording.
    
    Example duplicates caught:
    - "finish OAuth integration by tomorrow"
    - "complete the OAuth work tomorrow"
    """
    
    _embedder = None
    
    @staticmethod
    def _get_embedder():
        """Lazy-load sentence transformer embedder."""
        if Deduplicator._embedder is not None:
            return Deduplicator._embedder
        
        try:
            from sentence_transformers import SentenceTransformer
            Deduplicator._embedder = SentenceTransformer("all-mpnet-base-v2")
            return Deduplicator._embedder
        except ImportError:
            print("[!] Warning: sentence-transformers not available")
            print("[!] Falling back to string similarity matching")
            return None
    
    @staticmethod
    def semantic_similarity(text1: str, text2: str) -> float:
        """
        Compute semantic similarity using embeddings (0-1).
        
        Returns cosine similarity between sentence embeddings.
        Falls back to string similarity if embedder unavailable.
        
        Args:
            text1, text2: Texts to compare
        
        Returns:
            float: Similarity score (0-1)
        """
        embedder = Deduplicator._get_embedder()
        
        if embedder is None:
            # Fallback to simple string matching
            from difflib import SequenceMatcher
            return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        
        try:
            embeddings = embedder.encode([text1, text2])
            from sklearn.metrics.pairwise import cosine_similarity
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(similarity)
        except Exception as e:
            print(f"[!] Embedding failed: {e}")
            from difflib import SequenceMatcher
            return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    @staticmethod
    def are_duplicates(task1: Dict, task2: Dict, threshold: float = 0.8) -> bool:
        """
        Check if two tasks are semantic duplicates.
        
        Compares task descriptions using semantic similarity.
        
        Args:
            task1, task2: Task dictionaries
            threshold: Similarity threshold (0-1, default=0.8)
        
        Returns:
            bool: True if tasks are considered duplicates
        """
        desc1 = task1.get("task", "").strip()
        desc2 = task2.get("task", "").strip()
        
        if not desc1 or not desc2:
            return False
        
        if desc1.lower() == desc2.lower():
            return True
        
        similarity = Deduplicator.semantic_similarity(desc1, desc2)
        return similarity >= threshold
    
    @staticmethod
    def deduplicate(tasks: List[Dict], threshold: float = 0.80) -> List[Dict]:
        """
        Remove semantic duplicate tasks in two passes.
        
        Pass 1: Exact title matching (catches duplicates like "Share API docs" twice)
        Pass 2: Semantic similarity (catches rephrased duplicates)
        
        Keeps the highest-confidence version when duplicates are found.
        
        Args:
            tasks (List[Dict]): List of task objects
            threshold (float): Semantic similarity threshold (0-1, default=0.80)
        
        Returns:
            List[Dict]: Deduplicated task list
        """
        if len(tasks) <= 1:
            return tasks
        
        unique_tasks = []
        skip_indices = set()
        
        # PASS 1: Exact title match (high precision, catches obvious duplicates)
        seen_titles = {}
        for i, task in enumerate(tasks):
            if i in skip_indices:
                continue
            
            title = task.get("task", "").lower().strip()
            if not title:
                unique_tasks.append(task)
                continue
            
            if title not in seen_titles:
                # First occurrence: keep the one with highest confidence
                seen_titles[title] = (i, task.get("confidence", 0))
                unique_tasks.append(task)
            else:
                # Duplicate found: mark for removal, compare confidence
                prev_idx, prev_conf = seen_titles[title]
                curr_conf = task.get("confidence", 0)
                
                if curr_conf > prev_conf:
                    # Current is better: remove previous, add current
                    unique_tasks = [t for t in unique_tasks if t.get("task", "").lower().strip() != title]
                    unique_tasks.append(task)
                    seen_titles[title] = (i, curr_conf)
                
                skip_indices.add(i)
        
        # PASS 2: Semantic similarity on remaining tasks
        final_tasks = []
        semantic_skip_indices = set()
        
        for i, task in enumerate(unique_tasks):
            if i in semantic_skip_indices:
                continue
            
            # Find semantically similar tasks among remaining
            similar_group = [i]
            for j in range(i + 1, len(unique_tasks)):
                if j not in semantic_skip_indices:
                    if Deduplicator.are_duplicates(task, unique_tasks[j], threshold=threshold):
                        similar_group.append(j)
            
            # Keep highest confidence task from similar group
            if similar_group:
                best_idx = max(similar_group, key=lambda idx: unique_tasks[idx].get("confidence", 0))
                final_tasks.append(unique_tasks[best_idx])
                semantic_skip_indices.update(similar_group)
                semantic_skip_indices.discard(best_idx)
        
        return final_tasks

