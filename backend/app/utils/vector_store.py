"""
Vector Store Service using ChromaDB for semantic search
Provides document embedding and similarity search capabilities
"""
import os
import sys

# Suppress warnings before import
os.environ['ANONYMIZED_TELEMETRY'] = 'False'
os.environ['PYTHONWARNINGS'] = 'ignore'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

import warnings
warnings.filterwarnings('ignore')
warnings.simplefilter('ignore')

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer


class VectorStore:
    def __init__(self, persist_directory: str = "./data/chroma_db"):
        """Initialize ChromaDB with persistent storage"""
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)

        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False,
            allow_reset=True,
            is_persistent=True
        ))

        # Use multilingual BGE-M3 model
        model_path = './models/bge-m3' if os.path.exists('./models/bge-m3') else 'BAAI/bge-m3'
        self.embedding_model = SentenceTransformer(
            model_path,
            trust_remote_code=True,
            use_auth_token=False,
            device='mps' if os.uname().machine == 'arm64' else 'cpu'
        )

        # ---- Custom Embedding Function ----
        class CustomEmbeddingFunction:
            def __init__(self, model):
                self.model = model

            def name(self):
                return "bge-m3"

            def embed_query(self, input):
                """Embed a single query - called by ChromaDB for search"""
                text = input if isinstance(input, str) else str(input)
                embedding = self.model.encode([text[:2000]], show_progress_bar=False)
                # Return as list of lists for ChromaDB compatibility
                return [embedding[0].tolist()]

            def __call__(self, input):
                if isinstance(input, str):
                    input = [input]

                # Safety: truncate overly large text inputs
                safe_input = []
                for txt in input:
                    if len(txt) > 2000:
                        safe_input.append(txt[:2000])
                    else:
                        safe_input.append(txt)

                # Batch encoding to avoid large memory load
                embeddings = []
                batch_size = 16
                for i in range(0, len(safe_input), batch_size):
                    batch = safe_input[i:i + batch_size]
                    batch_emb = self.model.encode(batch, show_progress_bar=False)
                    embeddings.extend(batch_emb)

                return [emb.tolist() for emb in embeddings]

        embedding_function = CustomEmbeddingFunction(self.embedding_model)

        self.collection = self.client.get_or_create_collection(
            name="financial_documents",
            metadata={"description": "Financial document chunks with embeddings"},
            embedding_function=embedding_function
        )

    # -----------------------
    # CHUNKING METHOD
    # -----------------------
    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50, max_chunk_len: int = 1000) -> List[str]:
        """
        Split text into overlapping chunks for better context retention,
        with a hard limit to prevent massive chunks.
        """
        paragraphs = text.split('\n\n')

        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            # Trim overly long paragraph
            if len(paragraph) > max_chunk_len:
                paragraph = paragraph[:max_chunk_len]

            if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = current_chunk[-overlap:] if len(current_chunk) > overlap else ""

            current_chunk += paragraph + "\n\n"

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # Safety: remove or truncate any leftover large chunks
        return [c[:max_chunk_len] for c in chunks if c.strip()]

    # -----------------------
    # ADD DOCUMENT
    # -----------------------
    def add_document(self, file_id: str, text: str, metadata: Dict[str, Any] = None):
        """Add document text as semantic chunks into vector DB"""
        self.remove_document(file_id)

        chunks = self._chunk_text(text)
        if not chunks:
            print("⚠️ No valid chunks generated.")
            return

        ids, documents, metadatas = [], [], []

        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue

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

        # Final safety: filter out massive texts (>5k chars)
        safe_docs, safe_ids, safe_meta = [], [], []
        for d, i, m in zip(documents, ids, metadatas):
            if len(d) <= 5000:
                safe_docs.append(d)
                safe_ids.append(i)
                safe_meta.append(m)

        if not safe_docs:
            print("⚠️ No safe documents to add (all were too large).")
            return

        self.collection.add(
            ids=safe_ids,
            documents=safe_docs,
            metadatas=safe_meta
        )

        print(f"📚 Added {len(safe_docs)} chunks for file_id: {file_id}")
        print(f"   First chunk preview: {safe_docs[0][:120]}...")

    # -----------------------
    # SEARCH
    # -----------------------
    def search(self, query: str, file_ids: List[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Semantic search for relevant chunks"""
        where_filter = {"file_id": {"$in": file_ids}} if file_ids else None

        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_filter
        )

        formatted_results = []
        if results and results.get('documents') and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                formatted_results.append({
                    "text": doc,
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i],
                    "id": results['ids'][0][i]
                })
        return formatted_results

    # -----------------------
    # REMOVE / CLEAR
    # -----------------------
    def remove_document(self, file_id: str):
        """Remove all chunks of a document from vector DB"""
        try:
            results = self.collection.get(where={"file_id": file_id})
            if results and results['ids']:
                self.collection.delete(ids=results['ids'])
        except Exception:
            pass

    def get_document_count(self) -> int:
        """Count unique documents"""
        all_metadata = self.collection.get()
        if all_metadata and all_metadata['metadatas']:
            unique_files = set(m['file_id'] for m in all_metadata['metadatas'] if 'file_id' in m)
            return len(unique_files)
        return 0

    def clear_all(self):
        """Clear and recreate collection"""
        self.client.delete_collection("financial_documents")

        class CustomEmbeddingFunction:
            def __init__(self, model):
                self.model = model

            def name(self):
                return "bge-m3"

            def embed_query(self, input):
                """Embed a single query - called by ChromaDB for search"""
                text = input if isinstance(input, str) else str(input)
                embedding = self.model.encode([text[:2000]], show_progress_bar=False)
                # Return as list of lists for ChromaDB compatibility
                return [embedding[0].tolist()]

            def __call__(self, input):
                if isinstance(input, str):
                    input = [input]

                # Safety truncate
                safe_input = [txt[:2000] for txt in input]
                embeddings = self.model.encode(safe_input, show_progress_bar=False)
                return embeddings.tolist()

        embedding_function = CustomEmbeddingFunction(self.embedding_model)

        self.collection = self.client.get_or_create_collection(
            name="financial_documents",
            metadata={"description": "Financial document chunks with embeddings"},
            embedding_function=embedding_function
        )


# Singleton pattern
_vector_store_instance = None

def get_vector_store() -> VectorStore:
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance
