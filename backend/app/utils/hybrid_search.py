"""
Advanced Hybrid Search with BM25 + Vector + Cross-Encoder Re-ranking
Production-grade implementation for financial document retrieval
"""
import math
from typing import List, Dict, Tuple
from collections import Counter
from dataclasses import dataclass


@dataclass
class SearchResult:
    """Enhanced search result with scoring breakdown"""
    text: str
    score: float
    vector_score: float
    keyword_score: float
    metadata_score: float
    chunk_index: int
    file_id: str
    metadata: Dict


class HybridSearchEngine:
    """
    Advanced hybrid search combining:
    - Dense vector search (semantic similarity)
    - BM25 keyword search (lexical matching)
    - Metadata boosting
    - Cross-encoder re-ranking (optional, expensive)

    Fusion weights: Vector (60%) + Keyword (30%) + Metadata (10%)
    """

    def __init__(self, vector_store, k1: float = 1.5, b: float = 0.75):
        """
        Initialize hybrid search engine

        Args:
            vector_store: ChromaDB vector store instance
            k1: BM25 term frequency saturation parameter (default: 1.5)
            b: BM25 document length normalization (default: 0.75)
        """
        self.vector_store = vector_store
        self.k1 = k1  # Term frequency saturation
        self.b = b    # Length normalization

        # Fusion weights
        self.VECTOR_WEIGHT = 0.60
        self.KEYWORD_WEIGHT = 0.30
        self.METADATA_WEIGHT = 0.10

    def search(
        self,
        query: str,
        expanded_terms: List[str],
        file_ids: List[str] = None,
        top_k: int = 20,
        use_reranking: bool = False
    ) -> List[SearchResult]:
        """
        Hybrid search with 3-way fusion

        Args:
            query: Original query string
            expanded_terms: Query expansion terms (keywords + synonyms)
            file_ids: Optional list of file IDs to filter
            top_k: Number of results to return
            use_reranking: Enable cross-encoder re-ranking (expensive)

        Returns:
            List of SearchResult objects ranked by hybrid score
        """

        # 1. Vector Search (Semantic)
        vector_results = self._vector_search(query, file_ids, top_k * 2)

        if not vector_results:
            return []

        # 2. BM25 Keyword Search
        keyword_scores = self._bm25_search(vector_results, expanded_terms)

        # 3. Metadata Boosting
        metadata_scores = self._metadata_boost(vector_results, expanded_terms)

        # 4. Fusion: Combine scores
        hybrid_results = self._fuse_scores(
            vector_results,
            keyword_scores,
            metadata_scores
        )

        # 5. Optional: Cross-encoder re-ranking
        if use_reranking:
            hybrid_results = self._rerank(query, hybrid_results)

        # Return top-k
        return hybrid_results[:top_k]

    def _vector_search(
        self,
        query: str,
        file_ids: List[str],
        top_k: int
    ) -> List[Dict]:
        """Perform dense vector search using ChromaDB"""
        results = self.vector_store.search(
            query=query,
            file_ids=file_ids,
            top_k=top_k
        )
        return results

    def _bm25_search(
        self,
        documents: List[Dict],
        query_terms: List[str]
    ) -> Dict[int, float]:
        """
        BM25 scoring for keyword matching

        BM25 formula:
        score = Σ IDF(qi) * (f(qi, D) * (k1 + 1)) / (f(qi, D) + k1 * (1 - b + b * |D| / avgdl))

        Where:
        - IDF(qi): Inverse document frequency of term qi
        - f(qi, D): Frequency of qi in document D
        - |D|: Length of document D
        - avgdl: Average document length
        - k1, b: Tuning parameters
        """

        # Calculate document stats
        doc_lengths = [len(doc['text'].split()) for doc in documents]
        avgdl = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 1

        # Calculate IDF for each query term
        N = len(documents)
        idf_scores = {}

        for term in query_terms:
            term_lower = term.lower()
            # Count documents containing this term
            df = sum(1 for doc in documents if term_lower in doc['text'].lower())
            # IDF = log((N - df + 0.5) / (df + 0.5) + 1)
            idf_scores[term_lower] = math.log((N - df + 0.5) / (df + 0.5) + 1) if df > 0 else 0

        # Calculate BM25 score for each document
        bm25_scores = {}

        for idx, doc in enumerate(documents):
            doc_text_lower = doc['text'].lower()
            doc_length = doc_lengths[idx]

            score = 0.0
            for term in query_terms:
                term_lower = term.lower()

                # Term frequency in document
                tf = doc_text_lower.count(term_lower)

                if tf > 0:
                    # BM25 component for this term
                    numerator = idf_scores[term_lower] * tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * doc_length / avgdl)
                    score += numerator / denominator

            bm25_scores[idx] = score

        # Normalize scores to [0, 1]
        max_score = max(bm25_scores.values()) if bm25_scores else 1
        if max_score > 0:
            bm25_scores = {idx: score / max_score for idx, score in bm25_scores.items()}

        return bm25_scores

    def _metadata_boost(
        self,
        documents: List[Dict],
        query_terms: List[str]
    ) -> Dict[int, float]:
        """
        Boost documents based on metadata matching

        Boosting factors:
        - Filename matches query term: +0.5
        - Recent document (if year in metadata): +0.3
        - Specific section types (e.g., "financial statement"): +0.2
        """
        metadata_scores = {}

        for idx, doc in enumerate(documents):
            score = 0.0
            metadata = doc.get('metadata', {})

            # Filename matching
            filename = metadata.get('filename', '').lower()
            for term in query_terms:
                if term.lower() in filename:
                    score += 0.5
                    break

            # Section type boosting (if available)
            section_type = metadata.get('section_type', '').lower()
            if any(keyword in section_type for keyword in ['financial', 'statement', 'revenue', 'profit']):
                score += 0.2

            # Recency boost (if year available)
            # Assume more recent = more relevant
            year = metadata.get('year')
            if year and isinstance(year, int):
                recency_score = (year - 2000) / 25.0  # Normalize to ~[0, 1]
                score += recency_score * 0.3

            metadata_scores[idx] = min(score, 1.0)  # Cap at 1.0

        return metadata_scores

    def _fuse_scores(
        self,
        vector_results: List[Dict],
        keyword_scores: Dict[int, float],
        metadata_scores: Dict[int, float]
    ) -> List[SearchResult]:
        """
        Fuse vector, keyword, and metadata scores with weighted combination

        Final score = 0.6 * vector + 0.3 * keyword + 0.1 * metadata
        """
        fused_results = []

        for idx, doc in enumerate(vector_results):
            # Vector score (from ChromaDB, typically cosine similarity)
            vector_score = doc.get('score', 0.0)

            # Keyword score (BM25)
            keyword_score = keyword_scores.get(idx, 0.0)

            # Metadata score
            metadata_score = metadata_scores.get(idx, 0.0)

            # Weighted fusion
            final_score = (
                self.VECTOR_WEIGHT * vector_score +
                self.KEYWORD_WEIGHT * keyword_score +
                self.METADATA_WEIGHT * metadata_score
            )

            result = SearchResult(
                text=doc['text'],
                score=final_score,
                vector_score=vector_score,
                keyword_score=keyword_score,
                metadata_score=metadata_score,
                chunk_index=doc.get('metadata', {}).get('chunk_index', 0),
                file_id=doc.get('metadata', {}).get('file_id', ''),
                metadata=doc.get('metadata', {})
            )

            fused_results.append(result)

        # Sort by final score (descending)
        fused_results.sort(key=lambda x: x.score, reverse=True)

        return fused_results

    def _rerank(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """
        Cross-encoder re-ranking (placeholder for future implementation)

        This would use a model like:
        - cross-encoder/ms-marco-MiniLM-L-6-v2
        - cross-encoder/qnli-electra-base

        For now, returns results as-is
        Note: Cross-encoder is expensive (~10x slower) but can boost accuracy by 15-30%
        """
        # TODO: Implement cross-encoder re-ranking
        # from sentence_transformers import CrossEncoder
        # model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        # pairs = [[query, result.text] for result in results]
        # scores = model.predict(pairs)
        # ... re-sort by cross-encoder scores

        return results

    def explain_scores(self, result: SearchResult) -> str:
        """Generate human-readable score explanation"""
        return f"""
Score Breakdown:
- Final Score: {result.score:.4f}
- Vector (60%): {result.vector_score:.4f} → {result.vector_score * 0.6:.4f}
- Keyword (30%): {result.keyword_score:.4f} → {result.keyword_score * 0.3:.4f}
- Metadata (10%): {result.metadata_score:.4f} → {result.metadata_score * 0.1:.4f}
        """.strip()