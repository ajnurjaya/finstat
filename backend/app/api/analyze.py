import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from app.utils import DocumentParser, AIAnalyzer, DocumentCache
from app.utils.vector_store import get_vector_store

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")


class AnalyzeRequest(BaseModel):
    file_id: str
    analysis_type: Optional[str] = "comprehensive"  # summary, insights, or comprehensive


@router.post("/analyze")
async def analyze_document(request: AnalyzeRequest):
    """
    Analyze a financial statement and generate AI-powered summary and insights
    """
    try:
        # Find the uploaded file
        upload_path = Path(UPLOAD_DIR)
        files = list(upload_path.glob(f"{request.file_id}.*"))

        if not files:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = str(files[0])

        # Check if document already exists in ChromaDB
        vector_store = get_vector_store()
        test_search = vector_store.search(query=".", file_ids=[request.file_id], top_k=1)

        if test_search and len(test_search) > 0:
            # Document already parsed and stored, retrieve it
            print(f"📋 Document already in ChromaDB, retrieving {request.file_id}")
            all_chunks = vector_store.collection.get(where={"file_id": request.file_id})

            if all_chunks and all_chunks.get('documents'):
                chunk_data = list(zip(all_chunks['documents'], all_chunks['metadatas']))
                chunk_data.sort(key=lambda x: x[1].get('chunk_index', 0))
                document_text = '\n\n'.join([chunk for chunk, _ in chunk_data])

                metadata = all_chunks['metadatas'][0] if all_chunks['metadatas'] else {}
                parse_result = {
                    "format": metadata.get("format", "unknown"),
                    "page_count": metadata.get("page_count")
                }
            else:
                # Fallback to parsing
                print(f"📄 ChromaDB data incomplete, parsing {request.file_id}")
                parser = DocumentParser()
                parse_result = parser.parse_document(file_path)

                if not parse_result["success"]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Document parsing failed: {parse_result.get('error', 'Unknown error')}"
                    )

                document_text = parse_result["text"]

                vector_store.add_document(
                    file_id=request.file_id,
                    text=document_text,
                    metadata={
                        "filename": files[0].name,
                        "format": parse_result.get("format"),
                        "page_count": parse_result.get("page_count")
                    }
                )
        else:
            # Document not in ChromaDB, parse it
            print(f"📄 Parsing new document {request.file_id}")
            parser = DocumentParser()
            parse_result = parser.parse_document(file_path)

            if not parse_result["success"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Document parsing failed: {parse_result.get('error', 'Unknown error')}"
                )

            document_text = parse_result["text"]

            # Store document in vector database for semantic search
            vector_store.add_document(
                file_id=request.file_id,
                text=document_text,
                metadata={
                    "filename": files[0].name,
                    "format": parse_result.get("format"),
                    "page_count": parse_result.get("page_count")
                }
            )

        # Initialize AI analyzer
        analyzer = AIAnalyzer()

        # Perform analysis based on type
        if request.analysis_type == "summary":
            result = analyzer.summarize_financial_statement(document_text)
        elif request.analysis_type == "insights":
            result = analyzer.extract_insights(document_text)
        elif request.analysis_type == "comprehensive":
            result = analyzer.comprehensive_analysis(document_text)
        else:
            raise HTTPException(status_code=400, detail="Invalid analysis type")

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Analysis failed: {result.get('error', 'Unknown error')}"
            )

        # Prepare response
        response_data = {
            "success": True,
            "file_id": request.file_id,
            "analysis_type": request.analysis_type,
            "document_info": {
                "format": parse_result.get("format"),
                "page_count": parse_result.get("page_count"),
                "text_length": len(document_text)
            },
            "ai_info": {
                "provider": result.get("provider"),
                "model": result.get("model")
            }
        }

        # Add analysis results based on type
        if request.analysis_type == "summary":
            response_data["summary"] = result.get("summary")
        elif request.analysis_type == "insights":
            response_data["insights"] = result.get("insights")
        elif request.analysis_type == "comprehensive":
            response_data["full_analysis"] = result.get("full_analysis")
            response_data["sections"] = result.get("sections", {})

        return JSONResponse(status_code=200, content=response_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/analyze/{file_id}/text")
async def get_document_text(file_id: str):
    """
    Get the extracted text from a document without AI analysis
    """
    try:
        # Find the uploaded file
        upload_path = Path(UPLOAD_DIR)
        files = list(upload_path.glob(f"{file_id}.*"))

        if not files:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = str(files[0])

        # Try to get from ChromaDB first
        vector_store = get_vector_store()
        test_search = vector_store.search(query=".", file_ids=[file_id], top_k=1)

        if test_search and len(test_search) > 0:
            # Document exists in ChromaDB, retrieve all chunks
            print(f"📋 Retrieving text from ChromaDB for {file_id}")
            all_chunks = vector_store.collection.get(where={"file_id": file_id})

            if all_chunks and all_chunks.get('documents'):
                # Reconstruct full text from chunks (sorted by chunk_index)
                chunk_data = list(zip(all_chunks['documents'], all_chunks['metadatas']))
                chunk_data.sort(key=lambda x: x[1].get('chunk_index', 0))
                document_text = '\n\n'.join([chunk for chunk, _ in chunk_data])

                metadata = all_chunks['metadatas'][0] if all_chunks['metadatas'] else {}

                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "file_id": file_id,
                        "text": document_text,
                        "format": metadata.get("format", "unknown"),
                        "page_count": metadata.get("page_count"),
                        "metadata": {k: v for k, v in metadata.items() if k not in ["file_id", "chunk_index", "total_chunks"]}
                    }
                )

        # Not in ChromaDB, parse document
        print(f"📄 Text not in ChromaDB, parsing {file_id}")
        parser = DocumentParser()
        parse_result = parser.parse_document(file_path)

        if not parse_result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Document parsing failed: {parse_result.get('error', 'Unknown error')}"
            )

        # Add to ChromaDB for future use
        vector_store.add_document(
            file_id=file_id,
            text=parse_result["text"],
            metadata={
                "format": parse_result.get("format"),
                "page_count": parse_result.get("page_count")
            }
        )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "file_id": file_id,
                "text": parse_result["text"],
                "format": parse_result.get("format"),
                "page_count": parse_result.get("page_count"),
                "metadata": {
                    k: v for k, v in parse_result.items()
                    if k not in ["text", "success", "pages"]
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text extraction failed: {str(e)}")
