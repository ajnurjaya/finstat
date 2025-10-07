#!/usr/bin/env python3
"""
Reset Vector Database Script

This script clears the existing vector database to allow re-indexing
with the new multilingual embedding model.

Usage:
    python reset_vector_db.py
"""

import os
import shutil
from pathlib import Path

def reset_vector_db():
    """Remove the ChromaDB directory to force re-indexing"""

    chroma_dir = Path("./data/chroma_db")

    if chroma_dir.exists():
        print(f"🗑️  Removing old vector database at: {chroma_dir}")
        shutil.rmtree(chroma_dir)
        print("✅ Vector database cleared successfully!")
        print("\n📝 Next steps:")
        print("1. Restart your backend server")
        print("2. Re-analyze all your documents (they will be auto-indexed)")
        print("3. Test queries - should now find information correctly!")
    else:
        print(f"ℹ️  No vector database found at: {chroma_dir}")
        print("Database will be created automatically when you analyze documents.")

if __name__ == "__main__":
    print("=" * 60)
    print("Vector Database Reset Utility")
    print("=" * 60)
    print()

    # Confirm with user
    response = input("⚠️  This will delete all vector embeddings. Continue? (y/N): ")

    if response.lower() in ['y', 'yes']:
        reset_vector_db()
    else:
        print("❌ Operation cancelled.")