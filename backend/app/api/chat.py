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
from app.utils.query_processor import FinancialQueryProcessor
from app.utils.hybrid_search import HybridSearchEngine

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


class ChatAllRequest(BaseModel):
    file_ids: List[str]
    question: str


class ChatResponse(BaseModel):
    success: bool
    answer: str
    conversation_id: str
    file_id: str


def _find_relevant_context_optimized(file_id: str, question: str, document_text: str, max_chars: int = 20000) -> tuple[str, list, dict]:
    """
    OPTIMIZED Hybrid Search with:
    - Financial query processing
    - BM25 keyword scoring
    - 3-way fusion (Vector 60% + Keyword 30% + Metadata 10%)
    """
    vector_store = get_vector_store()

    # 1. Analyze query with financial domain awareness
    query_processor = FinancialQueryProcessor()
    analysis = query_processor.analyze(question)

    print(f"\n🔍 Optimized Hybrid Search:")
    print(f"   Query: {question}")
    print(f"   Intent: {analysis.intent}")
    print(f"   Keywords: {analysis.keywords}")
    print(f"   Expanded Terms: {analysis.expanded_terms}")
    print(f"   Cross-doc: {analysis.is_cross_document}")

    # 2. Perform advanced hybrid search
    hybrid_engine = HybridSearchEngine(vector_store)
    search_results = hybrid_engine.search(
        query=question,
        expanded_terms=analysis.expanded_terms,
        file_ids=[file_id],
        top_k=15,
        use_reranking=False  # Enable later for +15-30% accuracy
    )

    if not search_results:
        print("   ⚠️  No results found")
        return "", [], {}

    # 3. Combine top results into context
    combined_chunks = []
    total_chars = 0

    for result in search_results:
        if total_chars + len(result.text) <= max_chars:
            combined_chunks.append(result.text)
            total_chars += len(result.text)
        else:
            # Add partial chunk
            remaining = max_chars - total_chars
            if remaining > 100:
                combined_chunks.append(result.text[:remaining])
            break

    # Log score breakdown for top result
    if search_results:
        top_result = search_results[0]
        print(f"\n   📊 Top Result Scores:")
        print(f"      Final: {top_result.score:.4f}")
        print(f"      Vector: {top_result.vector_score:.4f}")
        print(f"      Keyword (BM25): {top_result.keyword_score:.4f}")
        print(f"      Metadata: {top_result.metadata_score:.4f}")

    print(f"   ✅ Retrieved {len(combined_chunks)} chunks ({total_chars} chars)")

    # Convert SearchResult objects to dict for logging
    results_for_logging = [
        {'text': r.text, 'score': r.score, 'metadata': r.metadata}
        for r in search_results
    ]

    analysis_dict = {
        'intent': analysis.intent,
        'keywords': analysis.keywords,
        'expanded_terms': analysis.expanded_terms,
        'is_cross_document': analysis.is_cross_document
    }

    return '\n\n'.join(combined_chunks), results_for_logging, analysis_dict


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

        # Search for relevant context using OPTIMIZED hybrid search
        # Financial-aware + BM25 + 3-way fusion for maximum accuracy
        relevant_context, vector_results, analysis_dict = _find_relevant_context_optimized(request.file_id, request.question, document_text)

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
            keyword_matches=analysis_dict.get('keywords', []),
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


@router.post("/chat-all")
async def chat_with_all_documents(request: ChatAllRequest):
    """
    Two-stage RAG for cross-document queries:
    Stage 1: Extract relevant info from each document
    Stage 2: Synthesize and compare extracted data
    """
    start_time = time.time()

    try:
        if not request.file_ids or len(request.file_ids) == 0:
            raise HTTPException(status_code=400, detail="No documents selected")

        upload_path = Path(UPLOAD_DIR)
        vector_store = get_vector_store()
        analyzer = AIAnalyzer()

        # STAGE 1: Extract relevant data from each document
        extracted_data = []

        for file_id in request.file_ids:
            # Get document metadata for display
            files = list(upload_path.glob(f"{file_id}.*"))
            if not files:
                continue

            # Load original filename from metadata cache
            from app.utils import DocumentCache
            metadata = DocumentCache.load_metadata(file_id)
            file_name = metadata.get("original_filename") if metadata else files[0].name

            # Get document text from ChromaDB
            cache_key = f"doc_{file_id}"
            if cache_key in conversation_store:
                document_text = conversation_store[cache_key]["text"]
            else:
                test_search = vector_store.search(query=".", file_ids=[file_id], top_k=1)
                if test_search and len(test_search) > 0:
                    all_chunks = vector_store.collection.get(where={"file_id": file_id})
                    if all_chunks and all_chunks.get('documents'):
                        chunk_data = list(zip(all_chunks['documents'], all_chunks['metadatas']))
                        chunk_data.sort(key=lambda x: x[1].get('chunk_index', 0))
                        document_text = '\n\n'.join([chunk for chunk, _ in chunk_data])
                        conversation_store[cache_key] = {"text": document_text}
                    else:
                        continue
                else:
                    continue

            # Find relevant context for this document using optimized search
            relevant_context, _, _ = _find_relevant_context_optimized(file_id, request.question, document_text)

            # Extract specific information using LLM
            extraction_prompt = f"""Extract the specific information requested from this document.

DOCUMENT: {file_name}

DOCUMENT CONTENT:
{relevant_context[:15000]}

QUESTION: {request.question}

INSTRUCTIONS:
1. Extract ONLY the specific data requested (numbers, facts, names, etc.)
2. Be precise and concise - provide just the requested information
3. Include context labels (e.g., "Revenue: $X million" or "Year: 2023")
4. If information not found, state "Not found"

EXTRACTED INFORMATION:"""

            if analyzer.provider == "ollama":
                extracted_info = analyzer._call_ollama(extraction_prompt)
            elif analyzer.provider == "anthropic":
                response = analyzer.client.messages.create(
                    model=analyzer.model,
                    max_tokens=500,
                    messages=[{"role": "user", "content": extraction_prompt}]
                )
                extracted_info = response.content[0].text
            elif analyzer.provider == "openai":
                response = analyzer.client.chat.completions.create(
                    model=analyzer.model,
                    messages=[
                        {"role": "system", "content": "You are a data extraction assistant."},
                        {"role": "user", "content": extraction_prompt}
                    ],
                    max_tokens=500
                )
                extracted_info = response.choices[0].message.content
            else:
                raise HTTPException(status_code=500, detail="AI provider not configured")

            extracted_data.append({
                "file_id": file_id,
                "filename": file_name,
                "extracted_info": extracted_info
            })

        if len(extracted_data) == 0:
            raise HTTPException(status_code=404, detail="No valid documents found")

        # STAGE 2: Synthesize and compare extracted data
        synthesis_prompt = f"""You are a financial analyst. Compare and analyze the extracted data from multiple documents.

ORIGINAL QUESTION: {request.question}

EXTRACTED DATA FROM {len(extracted_data)} DOCUMENTS:

"""
        for item in extracted_data:
            synthesis_prompt += f"""
📄 **{item['filename']}:**
{item['extracted_info']}

"""

        synthesis_prompt += """
INSTRUCTIONS:
1. Compare and contrast the data across all documents
2. Highlight key differences and similarities
3. Provide insights and analysis
4. Use clear formatting with bullet points
5. If comparing numbers, calculate differences or percentages
6. Answer the original question comprehensively

COMPARATIVE ANALYSIS:"""

        # Get final synthesized answer
        if analyzer.provider == "ollama":
            final_answer = analyzer._call_ollama(synthesis_prompt)
        elif analyzer.provider == "anthropic":
            response = analyzer.client.messages.create(
                model=analyzer.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": synthesis_prompt}]
            )
            final_answer = response.content[0].text
        elif analyzer.provider == "openai":
            response = analyzer.client.chat.completions.create(
                model=analyzer.model,
                messages=[
                    {"role": "system", "content": "You are a financial analyst assistant."},
                    {"role": "user", "content": synthesis_prompt}
                ],
                max_tokens=2000
            )
            final_answer = response.choices[0].message.content
        else:
            raise HTTPException(status_code=500, detail="AI provider not configured")

        response_time_ms = (time.time() - start_time) * 1000

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "answer": final_answer,
                "documents_analyzed": len(extracted_data),
                "file_ids": request.file_ids,
                "response_time_ms": response_time_ms
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cross-document chat failed: {str(e)}")