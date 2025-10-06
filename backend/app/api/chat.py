import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional

from app.utils import DocumentParser, AIAnalyzer

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


def _find_relevant_context(document_text: str, question: str, max_chars: int = 15000) -> str:
    """
    Find the most relevant parts of the document for the question.
    Uses simple keyword matching and context extraction.
    """
    # Extract keywords from the question (simple approach)
    question_lower = question.lower()
    keywords = [word for word in question_lower.split() if len(word) > 3]

    # If document is short enough, return it all
    if len(document_text) <= max_chars:
        return document_text

    # Split document into chunks (paragraphs or sections)
    chunks = document_text.split('\n\n')

    # Score each chunk based on keyword matches
    scored_chunks = []
    for i, chunk in enumerate(chunks):
        chunk_lower = chunk.lower()
        score = 0

        # Count keyword matches
        for keyword in keywords:
            score += chunk_lower.count(keyword) * 10

        # Boost score for chunks near the beginning (often have key info)
        if i < 10:
            score += 5

        scored_chunks.append((score, chunk))

    # Sort by score (highest first)
    scored_chunks.sort(reverse=True, key=lambda x: x[0])

    # Collect top chunks until we hit the character limit
    relevant_text = []
    total_chars = 0

    for score, chunk in scored_chunks:
        if total_chars + len(chunk) > max_chars:
            break
        if score > 0:  # Only include chunks with some relevance
            relevant_text.append(chunk)
            total_chars += len(chunk)

    # If we didn't find enough relevant text, include beginning of document
    if total_chars < max_chars // 2:
        relevant_text.insert(0, document_text[:max_chars // 2])

    return '\n\n'.join(relevant_text)[:max_chars]


@router.post("/chat")
async def chat_with_document(request: ChatRequest):
    """
    Ask questions about a specific document using AI
    """
    try:
        # Find the uploaded file
        upload_path = Path(UPLOAD_DIR)
        files = list(upload_path.glob(f"{request.file_id}.*"))

        if not files:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = str(files[0])

        # Parse document if not already cached
        cache_key = f"doc_{request.file_id}"
        if cache_key not in conversation_store:
            parser = DocumentParser()
            parse_result = parser.parse_document(file_path)

            if not parse_result["success"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Document parsing failed: {parse_result.get('error', 'Unknown error')}"
                )

            # Cache the document text
            conversation_store[cache_key] = {
                "text": parse_result["text"],
                "format": parse_result.get("format")
            }

        document_text = conversation_store[cache_key]["text"]

        # Get or create conversation history
        conv_id = request.conversation_id or f"conv_{request.file_id}"
        if conv_id not in conversation_store:
            conversation_store[conv_id] = []

        # Build context with conversation history
        conversation_history = conversation_store[conv_id]

        # Search for relevant context in the document
        # This helps when the document is very long
        relevant_context = _find_relevant_context(document_text, request.question)

        # Create prompt with document context
        context_prompt = f"""You are a financial analyst assistant. Answer questions about the following financial document.

FINANCIAL DOCUMENT:
{relevant_context}

CONVERSATION HISTORY:
"""
        # Add previous Q&A to context
        for msg in conversation_history[-3:]:  # Last 3 exchanges for context
            context_prompt += f"{msg['role'].upper()}: {msg['content']}\n"

        context_prompt += f"\nUSER QUESTION: {request.question}\n\nProvide a clear, concise answer based on the document above. If the information is not in the document, say so."

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