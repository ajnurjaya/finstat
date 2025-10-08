"""
Document Cache - Store parsed document data to avoid re-parsing
"""
import json
import pickle
from pathlib import Path
from typing import Dict, Any, Optional
import os

CACHE_DIR = os.getenv("CACHE_DIR", "./data/cache")
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)


class DocumentCache:
    """Cache for parsed document data"""

    @staticmethod
    def get_cache_path(file_id: str, cache_type: str = "tables") -> Path:
        """Get cache file path for a document"""
        return Path(CACHE_DIR) / f"{file_id}_{cache_type}.pkl"

    @staticmethod
    def save_tables(file_id: str, tables_data: list):
        """Save extracted tables to cache"""
        try:
            cache_path = DocumentCache.get_cache_path(file_id, "tables")
            with open(cache_path, 'wb') as f:
                pickle.dump(tables_data, f)
            print(f"💾 Cached tables for {file_id}")
            return True
        except Exception as e:
            print(f"⚠️  Failed to cache tables: {str(e)}")
            return False

    @staticmethod
    def load_tables(file_id: str) -> Optional[list]:
        """Load cached tables if available"""
        try:
            cache_path = DocumentCache.get_cache_path(file_id, "tables")
            if cache_path.exists():
                with open(cache_path, 'rb') as f:
                    tables = pickle.load(f)
                print(f"📋 Loaded {len(tables)} cached tables for {file_id}")
                return tables
            return None
        except Exception as e:
            print(f"⚠️  Failed to load cached tables: {str(e)}")
            return None

    @staticmethod
    def save_metadata(file_id: str, metadata: Dict[str, Any]):
        """Save document metadata (filename, format, etc.)"""
        try:
            cache_path = Path(CACHE_DIR) / f"{file_id}_metadata.json"
            with open(cache_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            return True
        except Exception as e:
            print(f"⚠️  Failed to save metadata: {str(e)}")
            return False

    @staticmethod
    def load_metadata(file_id: str) -> Optional[Dict[str, Any]]:
        """Load document metadata"""
        try:
            cache_path = Path(CACHE_DIR) / f"{file_id}_metadata.json"
            if cache_path.exists():
                with open(cache_path, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"⚠️  Failed to load metadata: {str(e)}")
            return None

    @staticmethod
    def clear_cache(file_id: str):
        """Clear all cached data for a document"""
        try:
            cache_dir = Path(CACHE_DIR)
            for cache_file in cache_dir.glob(f"{file_id}_*"):
                cache_file.unlink()
            print(f"🗑️  Cleared cache for {file_id}")
            return True
        except Exception as e:
            print(f"⚠️  Failed to clear cache: {str(e)}")
            return False

    @staticmethod
    def has_cached_tables(file_id: str) -> bool:
        """Check if tables are cached for a document"""
        cache_path = DocumentCache.get_cache_path(file_id, "tables")
        return cache_path.exists()