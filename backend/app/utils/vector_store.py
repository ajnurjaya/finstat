"""
Vector Store Service using ChromaDB for semantic search
Provides document embedding and similarity search capabilities
"""
import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import hashlib
from sentence_transformers import SentenceTransformer

# Disable ChromaDB telemetry to avoid warnings
os.environ['ANONYMIZED_TELEMETRY'] = 'False'

# Suppress torch.load security warning for trusted HuggingFace models
# We're only loading models from trusted sources (HuggingFace/local)
import warnings
warnings.filterwarnings('ignore', message='.*torch.load.*')

class VectorStore:
    def __init__(self, persist_directory: str = "./data/chroma_db"):
        """Initialize ChromaDB with persistent storage"""
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)

        # Initialize ChromaDB client with persistence and disabled telemetry
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False,
            allow_reset=True,
            is_persistent=True
        ))

        # Use BAAI/bge-m3 - state-of-the-art multilingual embedding model
        # Excellent for Indonesian, English, and 100+ languages
        # trust_remote_code=True allows loading from local/HuggingFace with safetensors
        model_path = './models/bge-m3' if os.path.exists('./models/bge-m3') else 'BAAI/bge-m3'
        self.embedding_model = SentenceTransformer(model_path, trust_remote_code=True)

        # Create custom embedding function for ChromaDB
        from chromadb.utils import embedding_functions

        class CustomEmbeddingFunction:
            def __init__(self, model):
                self.model = model

            def __call__(self, input):
                # Handle both single string and list of strings
                if isinstance(input, str):
                    input = [input]
                embeddings = self.model.encode(input, show_progress_bar=False)
                return embeddings.tolist()

        embedding_function = CustomEmbeddingFunction(self.embedding_model)

        # Get or create collection with custom embedding function
        self.collection = self.client.get_or_create_collection(
            name="financial_documents",
            metadata={"description": "Financial document chunks with embeddings"},
            embedding_function=embedding_function
        )

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks for better context retention

        Args:
            text: Document text to chunk
            chunk_size: Target size of each chunk in characters
            overlap: Number of characters to overlap between chunks

        Returns:
            List of text chunks
        """
        # Split by paragraphs first
        paragraphs = text.split('\n\n')

        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            # If adding this paragraph exceeds chunk size, save current chunk
            if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Keep overlap from end of previous chunk
                current_chunk = current_chunk[-overlap:] if len(current_chunk) > overlap else ""

            current_chunk += paragraph + "\n\n"

        # Add remaining text
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def add_document(self, file_id: str, text: str, metadata: Dict[str, Any] = None):
        """
        Add a document to the vector store

        Args:
            file_id: Unique identifier for the document
            text: Full text content of the document
            metadata: Additional metadata (filename, format, etc.)
        """
        # Remove existing document chunks if any
        self.remove_document(file_id)

        # Chunk the document
        chunks = self._chunk_text(text)

        if not chunks:
            return

        # Prepare data for ChromaDB
        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{file_id}_chunk_{i}"
            ids.append(chunk_id)
            documents.append(chunk)

            chunk_metadata = {
                "file_id": file_id,
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
            if metadata:
                chunk_metadata.update(metadata)
            metadatas.append(chunk_metadata)

        # Add to ChromaDB (it will generate embeddings automatically)
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

        print(f"📚 Added {len(chunks)} chunks to vector store for file_id: {file_id}")
        print(f"   First chunk preview: {chunks[0][:100]}...")

    def search(self, query: str, file_ids: List[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant document chunks using semantic similarity

        Args:
            query: Search query
            file_ids: Optional list of file IDs to filter by
            top_k: Number of top results to return

        Returns:
            List of relevant chunks with metadata and similarity scores
        """
        # Build where filter for specific documents
        where_filter = None
        if file_ids:
            where_filter = {"file_id": {"$in": file_ids}}

        # Perform semantic search
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_filter
        )

        # Format results
        formatted_results = []
        if results and results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                formatted_results.append({
                    "text": doc,
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if results['distances'] else 0,
                    "id": results['ids'][0][i] if results['ids'] else None
                })

        return formatted_results

    def remove_document(self, file_id: str):
        """Remove all chunks of a document from the vector store"""
        try:
            # Get all chunk IDs for this document
            results = self.collection.get(
                where={"file_id": file_id}
            )

            if results and results['ids']:
                self.collection.delete(ids=results['ids'])
        except Exception as e:
            # If document doesn't exist, that's fine
            pass

    def get_document_count(self) -> int:
        """Get total number of unique documents in the store"""
        all_metadata = self.collection.get()
        if all_metadata and all_metadata['metadatas']:
            unique_files = set(m['file_id'] for m in all_metadata['metadatas'] if 'file_id' in m)
            return len(unique_files)
        return 0

    def clear_all(self):
        """Clear all documents from the vector store"""
        self.client.delete_collection("financial_documents")

        # Recreate with same embedding function
        from chromadb.utils import embedding_functions

        class CustomEmbeddingFunction:
            def __init__(self, model):
                self.model = model

            def __call__(self, input):
                if isinstance(input, str):
                    input = [input]
                embeddings = self.model.encode(input, show_progress_bar=False)
                return embeddings.tolist()

        embedding_function = CustomEmbeddingFunction(self.embedding_model)

        self.collection = self.client.get_or_create_collection(
            name="financial_documents",
            metadata={"description": "Financial document chunks with embeddings"},
            embedding_function=embedding_function
        )


# Singleton instance
_vector_store_instance = None

def get_vector_store() -> VectorStore:
    """Get or create the vector store singleton instance"""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance