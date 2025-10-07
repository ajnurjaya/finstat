import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import List, Dict
from app.utils.vector_store import get_vector_store

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./outputs")


@router.get("/documents")
async def get_all_documents():
    """
    Get list of all uploaded documents with metadata
    """
    try:
        upload_path = Path(UPLOAD_DIR)

        if not upload_path.exists():
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "documents": [],
                    "total": 0
                }
            )

        documents = []

        # Get all files in upload directory
        for file_path in upload_path.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'):
                # Get file stats
                stats = file_path.stat()

                # Extract file_id (filename without extension)
                file_id = file_path.stem
                file_extension = file_path.suffix

                # Check if Excel export exists
                excel_file = Path(OUTPUT_DIR) / f"{file_id}_tables.xlsx"
                has_excel = excel_file.exists()

                doc_info = {
                    "file_id": file_id,
                    "filename": file_path.name,
                    "format": file_extension[1:].upper(),  # Remove dot
                    "size": stats.st_size,
                    "size_mb": round(stats.st_size / (1024 * 1024), 2),
                    "uploaded_at": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                    "has_excel": has_excel
                }

                documents.append(doc_info)

        # Sort by upload time (newest first)
        documents.sort(key=lambda x: x['uploaded_at'], reverse=True)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "documents": documents,
                "total": len(documents)
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get documents: {str(e)}")


@router.delete("/documents/{file_id}")
async def delete_document(file_id: str):
    """
    Delete a document and its associated files
    """
    try:
        upload_path = Path(UPLOAD_DIR)
        output_path = Path(OUTPUT_DIR)

        # Find and delete the main file
        files = list(upload_path.glob(f"{file_id}.*"))

        if not files:
            raise HTTPException(status_code=404, detail="Document not found")

        deleted_files = []

        # Delete main file
        for file in files:
            file.unlink()
            deleted_files.append(file.name)

        # Delete Excel file if exists
        excel_file = output_path / f"{file_id}_tables.xlsx"
        if excel_file.exists():
            excel_file.unlink()
            deleted_files.append(excel_file.name)

        # Remove from vector database
        vector_store = get_vector_store()
        vector_store.remove_document(file_id)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Document deleted successfully",
                "file_id": file_id,
                "deleted_files": deleted_files
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@router.get("/documents/{file_id}/info")
async def get_document_info(file_id: str):
    """
    Get detailed information about a specific document
    """
    try:
        upload_path = Path(UPLOAD_DIR)
        files = list(upload_path.glob(f"{file_id}.*"))

        if not files:
            raise HTTPException(status_code=404, detail="Document not found")

        file_path = files[0]
        stats = file_path.stat()

        # Check for Excel
        excel_file = Path(OUTPUT_DIR) / f"{file_id}_tables.xlsx"

        doc_info = {
            "file_id": file_id,
            "filename": file_path.name,
            "format": file_path.suffix[1:].upper(),
            "size": stats.st_size,
            "size_mb": round(stats.st_size / (1024 * 1024), 2),
            "uploaded_at": datetime.fromtimestamp(stats.st_mtime).isoformat(),
            "modified_at": datetime.fromtimestamp(stats.st_mtime).isoformat(),
            "has_excel": excel_file.exists(),
            "full_path": str(file_path)
        }

        return JSONResponse(status_code=200, content=doc_info)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document info: {str(e)}")