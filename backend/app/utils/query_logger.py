"""
Query Logger - Comprehensive logging for chatbot queries and responses
Tracks embedding model, LLM model, retrieved chunks, distances, and responses
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

class QueryLogger:
    def __init__(self, log_dir: str = "./logs/queries"):
        """Initialize query logger with persistent storage"""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create daily log file
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.log_file = self.log_dir / f"queries_{self.current_date}.jsonl"

    def log_query(
        self,
        question: str,
        answer: str,
        file_id: str,
        file_name: str,
        embedding_model: str,
        llm_model: str,
        llm_provider: str,
        vector_results: List[Dict[str, Any]],
        keyword_matches: List[str],
        total_context_chars: int,
        response_time_ms: float,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a complete query-response cycle with all details

        Args:
            question: User's question
            answer: LLM's answer
            file_id: Document file ID
            file_name: Document filename
            embedding_model: Name of embedding model used
            llm_model: Name of LLM model used
            llm_provider: LLM provider (ollama, openai, anthropic)
            vector_results: List of retrieved chunks with distances
            keyword_matches: List of keywords that matched
            total_context_chars: Total characters sent to LLM
            response_time_ms: Total response time in milliseconds
            conversation_id: Optional conversation ID
            metadata: Additional metadata

        Returns:
            Log entry ID (timestamp-based)
        """
        timestamp = datetime.now()
        entry_id = timestamp.strftime("%Y%m%d_%H%M%S_%f")

        # Prepare vector results summary
        vector_summary = []
        for i, result in enumerate(vector_results[:10]):  # Top 10 chunks
            full_text = result.get("text", "")
            vector_summary.append({
                "rank": i + 1,
                "chunk_id": result.get("id", "unknown"),
                "distance": round(result.get("distance", 0), 4),
                "text_preview": full_text[:150] + "..." if len(full_text) > 150 else full_text,
                "text_full": full_text,  # Store complete chunk text
                "text_length": len(full_text),
                "metadata": result.get("metadata", {})
            })

        # Create log entry
        log_entry = {
            "entry_id": entry_id,
            "timestamp": timestamp.isoformat(),
            "query": {
                "question": question,
                "file_id": file_id,
                "file_name": file_name,
                "conversation_id": conversation_id
            },
            "models": {
                "embedding_model": embedding_model,
                "llm_provider": llm_provider,
                "llm_model": llm_model
            },
            "retrieval": {
                "vector_results_count": len(vector_results),
                "keyword_matches": keyword_matches,
                "keyword_match_count": len(keyword_matches),
                "total_context_chars": total_context_chars,
                "top_chunks": vector_summary
            },
            "response": {
                "answer": answer,
                "answer_length": len(answer),
                "response_time_ms": round(response_time_ms, 2)
            },
            "metadata": metadata or {}
        }

        # Write to JSONL file (one JSON object per line)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

        # Also print to console for debugging
        self._print_log_summary(log_entry)

        return entry_id

    def _print_log_summary(self, entry: Dict[str, Any]):
        """Print a human-readable summary to console"""
        print(f"\n{'='*80}")
        print(f"📊 QUERY LOG - {entry['timestamp']}")
        print(f"{'='*80}")
        print(f"🔍 Question: {entry['query']['question']}")
        print(f"📄 Document: {entry['query']['file_name']} ({entry['query']['file_id']})")
        print(f"\n🤖 Models Used:")
        print(f"   • Embedding: {entry['models']['embedding_model']}")
        print(f"   • LLM: {entry['models']['llm_provider']}/{entry['models']['llm_model']}")
        print(f"\n🎯 Retrieval Results:")
        print(f"   • Vector results: {entry['retrieval']['vector_results_count']}")
        print(f"   • Keyword matches: {entry['retrieval']['keyword_match_count']} - {entry['retrieval']['keyword_matches']}")
        print(f"   • Context size: {entry['retrieval']['total_context_chars']} chars")
        print(f"\n📦 Top Retrieved Chunks:")
        for chunk in entry['retrieval']['top_chunks'][:3]:  # Show top 3
            print(f"   #{chunk['rank']} (distance: {chunk['distance']}): {chunk['text_preview']}")
        print(f"\n💬 Response:")
        print(f"   • Answer: {entry['response']['answer'][:200]}{'...' if len(entry['response']['answer']) > 200 else ''}")
        print(f"   • Response time: {entry['response']['response_time_ms']}ms")
        print(f"{'='*80}\n")

    def get_recent_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent log entries"""
        if not self.log_file.exists():
            return []

        logs = []
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))

        return logs[-limit:]  # Return last N entries

    def search_logs(
        self,
        question_contains: Optional[str] = None,
        file_id: Optional[str] = None,
        min_response_time: Optional[float] = None,
        date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search logs with filters"""
        # Determine which log file to search
        if date:
            log_file = self.log_dir / f"queries_{date}.jsonl"
        else:
            log_file = self.log_file

        if not log_file.exists():
            return []

        results = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue

                entry = json.loads(line)

                # Apply filters
                if question_contains and question_contains.lower() not in entry['query']['question'].lower():
                    continue
                if file_id and entry['query']['file_id'] != file_id:
                    continue
                if min_response_time and entry['response']['response_time_ms'] < min_response_time:
                    continue

                results.append(entry)

        return results

    def get_statistics(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics for logged queries"""
        logs = self.search_logs(date=date)

        if not logs:
            return {"total_queries": 0}

        response_times = [log['response']['response_time_ms'] for log in logs]
        context_sizes = [log['retrieval']['total_context_chars'] for log in logs]

        return {
            "total_queries": len(logs),
            "avg_response_time_ms": round(sum(response_times) / len(response_times), 2),
            "min_response_time_ms": round(min(response_times), 2),
            "max_response_time_ms": round(max(response_times), 2),
            "avg_context_size": round(sum(context_sizes) / len(context_sizes), 2),
            "models_used": {
                "embedding": list(set(log['models']['embedding_model'] for log in logs)),
                "llm": list(set(f"{log['models']['llm_provider']}/{log['models']['llm_model']}" for log in logs))
            }
        }


# Singleton instance
_logger_instance = None

def get_query_logger() -> QueryLogger:
    """Get or create the query logger singleton"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = QueryLogger()
    return _logger_instance