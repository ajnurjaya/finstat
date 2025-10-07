# view_full_chunks.py
import json
import sys
import os
from datetime import datetime
from pathlib import Path

def view_chunks(log_file, entry_num=-1):
    """View full chunks from a log entry"""
    # Check if file exists
    if not os.path.exists(log_file):
        print(f"❌ Error: Log file not found: {log_file}")

        # Try to find available log files
        log_dir = Path(log_file).parent
        if log_dir.exists():
            available_logs = sorted(log_dir.glob("queries_*.jsonl"))
            if available_logs:
                print(f"\n📂 Available log files:")
                for log in available_logs:
                    print(f"   • {log.name}")
                print(f"\nUsage: python {sys.argv[0]} logs/queries/queries_YYYY-MM-DD.jsonl")
            else:
                print(f"\n⚠️  No log files found in {log_dir}")
                print("Make sure to ask some questions first to generate logs!")
        return

    with open(log_file, 'r', encoding='utf-8') as f:
        logs = [json.loads(line) for line in f if line.strip()]

    if not logs:
        print(f"❌ No log entries found in {log_file}")
        return

    # Handle negative indexing and bounds
    if entry_num < 0:
        entry_num = len(logs) + entry_num

    if entry_num < 0 or entry_num >= len(logs):
        print(f"❌ Invalid entry number: {entry_num}")
        print(f"   Available entries: 0 to {len(logs)-1} (or -1 to -{len(logs)})")
        return

    entry = logs[entry_num]

    print(f"\n{'='*80}")
    print(f"📊 LOG ENTRY #{entry_num + 1} of {len(logs)}")
    print(f"{'='*80}")
    print(f"🕐 Timestamp: {entry['timestamp']}")
    print(f"🔍 Question: {entry['query']['question']}")
    print(f"📄 Document: {entry['query']['file_name']}")
    print(f"🤖 Models: {entry['models']['embedding_model']} + {entry['models']['llm_provider']}/{entry['models']['llm_model']}")
    print(f"⏱️  Response time: {entry['response']['response_time_ms']}ms")
    print(f"\n💬 Answer:\n{entry['response']['answer']}\n")
    print("=" * 80)
    print(f"📦 RETRIEVED CHUNKS (Top {len(entry['retrieval']['top_chunks'])} of {entry['retrieval']['vector_results_count']} results):\n")

    for chunk in entry['retrieval']['top_chunks']:
        print(f"{'─'*80}")

        # Handle both old and new log formats
        text_full = chunk.get('text_full', chunk.get('text_preview', 'N/A'))
        text_length = chunk.get('text_length', len(text_full) if text_full != 'N/A' else 0)

        print(f"Rank #{chunk['rank']} │ Distance: {chunk['distance']} │ Length: {text_length} chars")
        print(f"Chunk ID: {chunk['chunk_id']}")
        print(f"{'─'*80}")

        if text_full == 'N/A' or not text_full:
            print(f"\n⚠️  Full text not available (old log format - only preview saved)")
            print(f"Preview: {chunk.get('text_preview', 'N/A')}\n")
        else:
            print(f"\n{text_full}\n")

        print("=" * 80 + "\n")

if __name__ == "__main__":
    # Get today's date for default log file
    today = datetime.now().strftime("%Y-%m-%d")
    default_log = f"logs/queries/queries_{today}.jsonl"

    # Parse arguments
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
    else:
        log_file = default_log

    # Optional: specify which entry to view (default: last entry)
    entry_num = int(sys.argv[2]) if len(sys.argv) > 2 else -1

    view_chunks(log_file, entry_num)