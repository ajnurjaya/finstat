#!/usr/bin/env python3
"""
Inspect Vector Database Chunks
View all chunks stored in ChromaDB for a specific document
"""
import sys
from app.utils.vector_store import get_vector_store

def inspect_document_chunks(file_id: str = None):
    """
    Inspect all chunks in the vector database

    Args:
        file_id: Optional file ID to filter by specific document
    """
    vector_store = get_vector_store()

    # Get all data from the collection
    all_data = vector_store.collection.get(
        where={"file_id": file_id} if file_id else None,
        include=["documents", "metadatas", "embeddings"]
    )

    if not all_data['ids']:
        print(f"❌ No chunks found{f' for file_id: {file_id}' if file_id else ''}")
        print("\nℹ️  Make sure you have:")
        print("   1. Uploaded documents")
        print("   2. Analyzed them (to create embeddings)")
        return

    # Group chunks by file_id
    files = {}
    for i, chunk_id in enumerate(all_data['ids']):
        metadata = all_data['metadatas'][i]
        doc_file_id = metadata.get('file_id', 'unknown')

        if doc_file_id not in files:
            files[doc_file_id] = {
                'filename': metadata.get('filename', 'unknown'),
                'format': metadata.get('format', 'unknown'),
                'chunks': []
            }

        files[doc_file_id]['chunks'].append({
            'chunk_id': chunk_id,
            'chunk_index': metadata.get('chunk_index', 0),
            'total_chunks': metadata.get('total_chunks', 0),
            'text': all_data['documents'][i],
            'embedding_dims': len(all_data['embeddings'][i]) if all_data['embeddings'] else 0,
            'metadata': metadata
        })

    # Display results
    print(f"\n{'='*80}")
    print(f"📦 VECTOR DATABASE INSPECTION")
    print(f"{'='*80}")
    print(f"Total documents: {len(files)}")
    print(f"Total chunks: {len(all_data['ids'])}")
    print(f"{'='*80}\n")

    for file_id, file_data in files.items():
        # Sort chunks by index
        chunks = sorted(file_data['chunks'], key=lambda x: x['chunk_index'])

        print(f"\n{'█'*80}")
        print(f"📄 Document: {file_data['filename']}")
        print(f"   File ID: {file_id}")
        print(f"   Format: {file_data['format']}")
        print(f"   Total chunks: {len(chunks)}")
        print(f"{'█'*80}\n")

        for chunk in chunks:
            print(f"{'─'*80}")
            print(f"Chunk #{chunk['chunk_index'] + 1} of {chunk['total_chunks']}")
            print(f"Chunk ID: {chunk['chunk_id']}")
            print(f"Text length: {len(chunk['text'])} chars")
            print(f"Embedding dimensions: {chunk['embedding_dims']}")
            print(f"{'─'*80}")
            print(f"\nRAW CHUNK TEXT:")
            print(f"{chunk['text']}")
            print(f"\n{'='*80}\n")


def list_documents():
    """List all documents in the vector database"""
    vector_store = get_vector_store()

    all_data = vector_store.collection.get(
        include=["metadatas"]
    )

    if not all_data['ids']:
        print("❌ No documents found in vector database")
        return

    # Group by file_id
    files = {}
    for metadata in all_data['metadatas']:
        file_id = metadata.get('file_id', 'unknown')
        if file_id not in files:
            files[file_id] = {
                'filename': metadata.get('filename', 'unknown'),
                'format': metadata.get('format', 'unknown'),
                'chunk_count': 0
            }
        files[file_id]['chunk_count'] += 1

    print(f"\n{'='*80}")
    print(f"📚 DOCUMENTS IN VECTOR DATABASE")
    print(f"{'='*80}\n")

    for file_id, data in files.items():
        print(f"📄 {data['filename']}")
        print(f"   File ID: {file_id}")
        print(f"   Format: {data['format']}")
        print(f"   Chunks: {data['chunk_count']}")
        print(f"{'─'*80}")

    print(f"\nTotal: {len(files)} documents, {len(all_data['ids'])} chunks")
    print(f"\nUsage: python inspect_chunks.py <file_id>")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "list" or sys.argv[1] == "-l":
            # List all documents
            list_documents()
        else:
            # Inspect specific document
            file_id = sys.argv[1]
            inspect_document_chunks(file_id)
    else:
        # List all documents by default
        list_documents()