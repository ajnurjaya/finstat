import os
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional

from app.utils import DocumentParser, AIAnalyzer
from app.utils.vector_store import get_vector_store
from app.utils.query_logger import get_query_logger

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

# Store conversation history in memory (in production, use Redis or database)
conversation_store = {}


class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str


class ChatRequest(BaseModel):
    file_id: str
    question: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    success: bool
    answer: str
    conversation_id: str
    file_id: str


def _find_relevant_context_hybrid(file_id: str, question: str, document_text: str, max_chars: int = 20000) -> tuple[str, list, list]:
    """
    Hybrid search: Combines vector similarity search with keyword matching.
    This ensures we don't miss exact matches (like names) while leveraging semantic search.
    """
    vector_store = get_vector_store()

    # 1. Vector search for semantic similarity
    vector_results = vector_store.search(query=question, file_ids=[file_id], top_k=20)

    # Debug logging
    print(f"\n🔍 Hybrid Search Debug:")
    print(f"   Query: {question}")
    print(f"   File ID: {file_id}")
    print(f"   Vector results: {len(vector_results)}")

    # 2. Extract potential keywords (names, specific terms)
    import re
    # Look for capitalized words that might be names or specific terms
    keywords = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', question)
    print(f"   Detected keywords: {keywords}")

    # 3. Keyword-based boosting: Find chunks with exact keyword matches
    keyword_matched_chunks = []
    if keywords and document_text:
        doc_chunks = document_text.split('\n\n')
        for chunk in doc_chunks:
            for keyword in keywords:
                if keyword.lower() in chunk.lower():
                    keyword_matched_chunks.append(chunk)
                    print(f"   ✅ Keyword match found: '{keyword}' in chunk")
                    break

    # 4. Combine results: keyword matches first, then vector results
    combined_chunks = []
    total_chars = 0

    # Add keyword-matched chunks first (highest priority)
    for chunk in keyword_matched_chunks[:5]:  # Max 5 keyword chunks
        if total_chars + len(chunk) <= max_chars:
            combined_chunks.append(chunk)
            total_chars += len(chunk)

    # Then add vector search results
    for result in vector_results:
        chunk_text = result['text']
        # Skip if already added from keyword matching
        if chunk_text in combined_chunks:
            continue

        if total_chars + len(chunk_text) <= max_chars:
            combined_chunks.append(chunk_text)
            total_chars += len(chunk_text)
        else:
            # Add partial chunk to fill remaining space
            remaining = max_chars - total_chars
            if remaining > 100:
                combined_chunks.append(chunk_text[:remaining])
            break

    print(f"   ✅ Combined {len(combined_chunks)} chunks ({total_chars} chars)")
    print(f"      - {len(keyword_matched_chunks[:5])} from keyword matching")
    print(f"      - {len(combined_chunks) - len(keyword_matched_chunks[:5])} from vector search")

    if not combined_chunks:
        print("   ⚠️  No results found - returning empty context")
        return "", vector_results, keywords

    return '\n\n'.join(combined_chunks), vector_results, keywords


@router.post("/chat")
async def chat_with_document(request: ChatRequest):
    """
    Ask questions about a specific document using AI
    """
    start_time = time.time()

    try:
        # Find the uploaded file
        upload_path = Path(UPLOAD_DIR)
        files = list(upload_path.glob(f"{request.file_id}.*"))

        if not files:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = str(files[0])
        file_name = files[0].name

        # Get document text from ChromaDB or parse if not available
        cache_key = f"doc_{request.file_id}"

        # First check in-memory cache
        if cache_key in conversation_store:
            document_text = conversation_store[cache_key]["text"]
        else:
            # Try to get from ChromaDB by searching for any chunk
            vector_store = get_vector_store()
            test_search = vector_store.search(query=".", file_ids=[request.file_id], top_k=1)

            if test_search and len(test_search) > 0:
                # Document exists in ChromaDB, retrieve all chunks
                print(f"📋 Using cached document from ChromaDB for {request.file_id}")
                all_chunks = vector_store.collection.get(where={"file_id": request.file_id})
                if all_chunks and all_chunks.get('documents'):
                    # Reconstruct full text from chunks (sorted by chunk_index)
                    chunk_data = list(zip(all_chunks['documents'], all_chunks['metadatas']))
                    chunk_data.sort(key=lambda x: x[1].get('chunk_index', 0))
                    document_text = '\n\n'.join([chunk for chunk, _ in chunk_data])

                    # Cache in memory
                    conversation_store[cache_key] = {
                        "text": document_text,
                        "format": all_chunks['metadatas'][0].get('format', 'unknown') if all_chunks['metadatas'] else 'unknown'
                    }
                else:
                    # ChromaDB has metadata but no documents - parse again
                    raise Exception("ChromaDB data corrupted - no documents found")
            else:
                # Not in ChromaDB, need to parse
                print(f"📄 Document not in ChromaDB, parsing {request.file_id}")
                parser = DocumentParser()
                parse_result = parser.parse_document(file_path)

                if not parse_result["success"]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Document parsing failed: {parse_result.get('error', 'Unknown error')}"
                    )

                document_text = parse_result["text"]

                # Cache in memory
                conversation_store[cache_key] = {
                    "text": document_text,
                    "format": parse_result.get("format")
                }

                # Add to ChromaDB for future use
                vector_store.add_document(
                    file_id=request.file_id,
                    text=document_text,
                    metadata={"format": parse_result.get("format")}
                )

        # Get or create conversation history
        conv_id = request.conversation_id or f"conv_{request.file_id}"
        if conv_id not in conversation_store:
            conversation_store[conv_id] = []

        # Build context with conversation history
        conversation_history = conversation_store[conv_id]

        # Search for relevant context using hybrid search
        # Combines vector similarity with keyword matching for best accuracy
        relevant_context, vector_results, keywords = _find_relevant_context_hybrid(request.file_id, request.question, document_text)

        # Create prompt with document context
        context_prompt = f"""You are a helpful financial analyst assistant. Answer the user's question using ONLY the information provided in the document below.

DOCUMENT CONTEXT:
{relevant_context}

CONVERSATION HISTORY:
"""
        # Add previous Q&A to context
        for msg in conversation_history[-3:]:  # Last 3 exchanges for context
            context_prompt += f"{msg['role'].upper()}: {msg['content']}\n"

        context_prompt += f"""
QUESTION: {request.question}

INSTRUCTIONS:
1. Read the document context carefully
2. Extract the relevant information that answers the question
3. For factual questions (who, what, when, where): provide the specific information found in the document
4. For numerical questions: provide the EXACT numbers from the document - do not round or estimate
5. If the information is truly not in the document, say "Informasi tidak ditemukan dalam dokumen"
6. Be concise and direct in your answer

ANSWER:"""

        # Get AI response
        analyzer = AIAnalyzer()

        # Use the provider's chat method
        if analyzer.provider == "ollama":
            answer = analyzer._call_ollama(context_prompt)
        elif analyzer.provider == "anthropic":
            response = analyzer.client.messages.create(
                model=analyzer.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": context_prompt}]
            )
            answer = response.content[0].text
        elif analyzer.provider == "openai":
            response = analyzer.client.chat.completions.create(
                model=analyzer.model,
                messages=[
                    {"role": "system", "content": "You are a financial analyst assistant."},
                    {"role": "user", "content": context_prompt}
                ],
                max_tokens=1000
            )
            answer = response.choices[0].message.content
        else:
            raise HTTPException(status_code=500, detail="AI provider not configured")

        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000

        # Get embedding model info from vector store
        vector_store = get_vector_store()
        embedding_model_name = vector_store.embedding_model.model_name_or_path if hasattr(vector_store.embedding_model, 'model_name_or_path') else "BAAI/bge-m3"

        # Log the query with all details
        logger = get_query_logger()
        logger.log_query(
            question=request.question,
            answer=answer,
            file_id=request.file_id,
            file_name=file_name,
            embedding_model=embedding_model_name,
            llm_model=analyzer.model,
            llm_provider=analyzer.provider,
            vector_results=vector_results,
            keyword_matches=keywords,
            total_context_chars=len(relevant_context),
            response_time_ms=response_time_ms,
            conversation_id=conv_id
        )

        # Save to conversation history
        conversation_store[conv_id].append({"role": "user", "content": request.question})
        conversation_store[conv_id].append({"role": "assistant", "content": answer})

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "answer": answer,
                "conversation_id": conv_id,
                "file_id": request.file_id
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/chat/{conversation_id}/history")
async def get_chat_history(conversation_id: str):
    """
    Get conversation history for a specific conversation
    """
    try:
        if conversation_id not in conversation_store:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "conversation_id": conversation_id,
                    "messages": []
                }
            )

        messages = conversation_store[conversation_id]

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "conversation_id": conversation_id,
                "messages": messages
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


@router.delete("/chat/{conversation_id}")
async def clear_chat_history(conversation_id: str):
    """
    Clear conversation history
    """
    try:
        if conversation_id in conversation_store:
            del conversation_store[conversation_id]

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Conversation history cleared",
                "conversation_id": conversation_id
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {str(e)}")