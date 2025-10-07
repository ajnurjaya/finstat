# Query Logging System

Comprehensive logging system for tracking chatbot queries, responses, and performance metrics.

## Features

The query logger automatically tracks:

- ✅ **Question & Answer** - Full query-response pairs
- ✅ **Embedding Model** - Which embedding model was used (e.g., BAAI/bge-m3)
- ✅ **LLM Model** - Which LLM answered the question (e.g., ollama/llama3.1)
- ✅ **Vector Search Results** - Top retrieved chunks with distance scores
- ✅ **Keyword Matches** - Which keywords were detected and matched
- ✅ **Context Size** - How many characters were sent to the LLM
- ✅ **Response Time** - Total time to generate answer (milliseconds)
- ✅ **Document Info** - File ID and filename
- ✅ **Conversation ID** - Track multi-turn conversations

## Log Storage

Logs are stored in **JSONL format** (one JSON object per line):

```
backend/logs/queries/queries_2025-01-07.jsonl
```

Each day creates a new log file automatically.

## Example Log Entry

```json
{
  "entry_id": "20250107_143022_123456",
  "timestamp": "2025-01-07T14:30:22.123456",
  "query": {
    "question": "Who is Vikram Sinha?",
    "file_id": "c6c2b43b-565a-4e40-a809-93f955d5123b",
    "file_name": "financial_report.pdf",
    "conversation_id": "conv_c6c2b43b-565a-4e40-a809-93f955d5123b"
  },
  "models": {
    "embedding_model": "BAAI/bge-m3",
    "llm_provider": "ollama",
    "llm_model": "llama3.1"
  },
  "retrieval": {
    "vector_results_count": 20,
    "keyword_matches": ["Vikram", "Sinha"],
    "keyword_match_count": 2,
    "total_context_chars": 18556,
    "top_chunks": [
      {
        "rank": 1,
        "chunk_id": "c6c2b43b_chunk_42",
        "distance": 12.34,
        "text_preview": "Vikram Sinha serves as the Chief Financial Officer...",
        "metadata": {
          "file_id": "c6c2b43b-565a-4e40-a809-93f955d5123b",
          "chunk_index": 42,
          "total_chunks": 150
        }
      }
    ]
  },
  "response": {
    "answer": "Vikram Sinha is the Chief Financial Officer (CFO)...",
    "answer_length": 156,
    "response_time_ms": 2345.67
  },
  "metadata": {}
}
```

## Console Output

Each query also prints a human-readable summary to the console:

```
================================================================================
📊 QUERY LOG - 2025-01-07T14:30:22.123456
================================================================================
🔍 Question: Who is Vikram Sinha?
📄 Document: financial_report.pdf (c6c2b43b-565a-4e40-a809-93f955d5123b)

🤖 Models Used:
   • Embedding: BAAI/bge-m3
   • LLM: ollama/llama3.1

🎯 Retrieval Results:
   • Vector results: 20
   • Keyword matches: 2 - ['Vikram', 'Sinha']
   • Context size: 18556 chars

📦 Top Retrieved Chunks:
   #1 (distance: 12.34): Vikram Sinha serves as the Chief Financial Officer...
   #2 (distance: 15.67): Mr. Sinha has over 20 years of experience...
   #3 (distance: 18.91): Under Sinha's leadership, the company achieved...

💬 Response:
   • Answer: Vikram Sinha is the Chief Financial Officer (CFO)...
   • Response time: 2345.67ms
================================================================================
```

## API Endpoints

### 1. Get Recent Logs

```bash
GET /api/logs/recent?limit=10
```

**Response:**
```json
{
  "success": true,
  "count": 10,
  "logs": [ /* array of log entries */ ]
}
```

### 2. Search Logs

```bash
GET /api/logs/search?question=vikram&min_response_time=1000&date=2025-01-07
```

**Parameters:**
- `question` - Filter by question content (partial match)
- `file_id` - Filter by specific document
- `min_response_time` - Filter by minimum response time (ms)
- `date` - Filter by date (YYYY-MM-DD)

**Response:**
```json
{
  "success": true,
  "count": 5,
  "filters": {
    "question": "vikram",
    "file_id": null,
    "min_response_time": 1000,
    "date": "2025-01-07"
  },
  "logs": [ /* filtered log entries */ ]
}
```

### 3. Get Statistics

```bash
GET /api/logs/statistics?date=2025-01-07
```

**Response:**
```json
{
  "success": true,
  "date": "2025-01-07",
  "statistics": {
    "total_queries": 156,
    "avg_response_time_ms": 2134.56,
    "min_response_time_ms": 456.78,
    "max_response_time_ms": 8901.23,
    "avg_context_size": 15234.89,
    "models_used": {
      "embedding": ["BAAI/bge-m3"],
      "llm": ["ollama/llama3.1", "ollama/mistral"]
    }
  }
}
```

## Use Cases

### 1. Debug Inaccurate Answers

When a query returns wrong information:

1. Check the console output or log file
2. Review "Top Retrieved Chunks" to see what context was sent to LLM
3. Check distance scores - high distances mean poor semantic match
4. Verify keyword matches - did it find the right keywords?
5. Check context size - was enough context provided?

**Example:**
```json
{
  "question": "berapa aset lancar?",
  "retrieval": {
    "keyword_matches": ["aset", "lancar"],  // ✓ Keywords found
    "top_chunks": [
      {
        "rank": 1,
        "distance": 8.5,  // ✓ Good match (low distance)
        "text_preview": "Aset Lancar tahun 2025: Rp 15,332,166..."  // ✓ Contains answer!
      }
    ]
  },
  "response": {
    "answer": "15,332,166"  // ✓ Correct!
  }
}
```

### 2. Performance Optimization

Find slow queries:

```bash
curl "http://localhost:8000/api/logs/search?min_response_time=5000"
```

This shows queries taking >5 seconds, helping you identify:
- Documents that need better chunking
- Queries requiring more context
- Performance bottlenecks

### 3. Model Comparison

Compare different embedding models or LLMs:

```python
# Search logs for specific model
curl "http://localhost:8000/api/logs/search" | jq '.logs[] | select(.models.embedding_model == "BAAI/bge-m3")'

# Compare average response times
curl "http://localhost:8000/api/logs/statistics"
```

### 4. Analyze Retrieval Quality

Check if vector search is finding relevant chunks:

- **Low distance scores** (< 20) = Good semantic match
- **High distance scores** (> 50) = Poor match, may need re-indexing
- **Keyword matches** = Hybrid search working correctly

### 5. Track Conversation Flow

Use `conversation_id` to track multi-turn conversations:

```bash
curl "http://localhost:8000/api/logs/search" | jq '.logs[] | select(.query.conversation_id == "conv_abc123")'
```

## Integration

The logging happens automatically for every chat query. No code changes needed!

When you ask a question via:
- `/api/chat` endpoint
- Web interface chatbot
- Multi-document chat

The query is automatically logged with full details.

## Benefits

1. **Debugging** - Understand why answers are wrong
2. **Performance** - Track response times and optimize
3. **Quality** - Monitor retrieval accuracy with distance scores
4. **Analytics** - Understand usage patterns
5. **Auditing** - Full history of all queries and responses
6. **Model Comparison** - A/B test different models

## File Rotation

Logs are automatically rotated daily:
- `queries_2025-01-07.jsonl`
- `queries_2025-01-08.jsonl`
- `queries_2025-01-09.jsonl`

Old logs are kept indefinitely (you can manually delete if needed).

## Privacy Note

Logs contain:
- Full question text
- Full answer text
- Document names
- File IDs

**Do not commit log files to git** - they may contain sensitive information!

Add to `.gitignore`:
```
backend/logs/
```