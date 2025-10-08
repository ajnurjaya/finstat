import os
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
from app.utils import DocumentCache

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 50000000))  # 50MB default

# Ensure upload directory exists
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {'.pdf', '.txt', '.docx', '.doc'}


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a financial statement document (PDF, TXT, or DOCX)
    """
    try:
        # Validate file extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type not supported. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # Read file content
        contents = await file.read()

        # Check file size
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1000000}MB"
            )

        # Generate unique filename
        file_id = str(uuid.uuid4())
        original_filename = file.filename
        safe_filename = f"{file_id}{file_extension}"
        file_path = Path(UPLOAD_DIR) / safe_filename

        # Save file
        with open(file_path, 'wb') as f:
            f.write(contents)

        # Save metadata with original filename
        DocumentCache.save_metadata(file_id, {
            "original_filename": original_filename,
            "file_extension": file_extension,
            "file_size": len(contents),
            "file_type": file_extension[1:]
        })

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "File uploaded successfully",
                "file_id": file_id,
                "filename": original_filename,
                "file_path": str(file_path),
                "file_size": len(contents),
                "file_type": file_extension[1:]  # Remove the dot
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.delete("/upload/{file_id}")
async def delete_file(file_id: str):
    """
    Delete an uploaded file
    """
    try:
        # Find file with this ID
        upload_path = Path(UPLOAD_DIR)
        files = list(upload_path.glob(f"{file_id}.*"))

        if not files:
            raise HTTPException(status_code=404, detail="File not found")

        # Delete the file
        for file_path in files:
            file_path.unlink()

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "File deleted successfully",
                "file_id": file_id
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
