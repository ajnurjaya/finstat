import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from app.utils import TableExtractor

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./outputs")

# Ensure output directory exists
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


class ExtractTablesRequest(BaseModel):
    file_id: str


@router.post("/extract-tables")
async def extract_tables(request: ExtractTablesRequest):
    """
    Extract all tables from a document and export to Excel
    """
    try:
        # Find the uploaded file
        upload_path = Path(UPLOAD_DIR)
        files = list(upload_path.glob(f"{request.file_id}.*"))

        if not files:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = str(files[0])

        # Extract tables and export to Excel
        extractor = TableExtractor()
        result = extractor.extract_and_export(file_path, OUTPUT_DIR)

        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Table extraction failed")
            )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "file_id": request.file_id,
                "tables_count": result.get("tables_count", 0),
                "excel_file": result.get("filename"),
                "download_url": f"/api/download/{request.file_id}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Table extraction failed: {str(e)}")


@router.get("/download/{file_id}")
async def download_excel(file_id: str):
    """
    Download the extracted tables Excel file
    """
    try:
        # Find Excel file with this file_id
        output_path = Path(OUTPUT_DIR)
        excel_files = list(output_path.glob(f"*{file_id}*.xlsx"))

        if not excel_files:
            # Try to find by pattern
            excel_files = list(output_path.glob(f"{file_id}_tables.xlsx"))

        if not excel_files:
            # Look for any Excel file matching the pattern
            all_excel = list(output_path.glob("*.xlsx"))
            for excel_file in all_excel:
                if file_id in excel_file.stem:
                    excel_files = [excel_file]
                    break

        if not excel_files:
            raise HTTPException(
                status_code=404,
                detail="Excel file not found. Please extract tables first."
            )

        excel_path = excel_files[0]

        return FileResponse(
            path=str(excel_path),
            filename=excel_path.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.get("/tables/{file_id}/preview")
async def preview_tables(file_id: str):
    """
    Preview extracted tables without downloading Excel file
    """
    try:
        # Find the uploaded file
        upload_path = Path(UPLOAD_DIR)
        files = list(upload_path.glob(f"{file_id}.*"))

        if not files:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = str(files[0])
        file_extension = Path(file_path).suffix.lower()

        # Extract tables
        extractor = TableExtractor()

        if file_extension == '.pdf':
            tables = extractor.extract_tables_from_pdf(file_path)
        elif file_extension in ['.docx', '.doc']:
            tables = extractor.extract_tables_from_docx(file_path)
        elif file_extension == '.txt':
            tables = extractor.extract_tables_from_txt(file_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        # Convert DataFrames to JSON-serializable format
        tables_data = []
        for idx, df in enumerate(tables, 1):
            table_dict = {
                "table_number": idx,
                "page": df.attrs.get('page', None),
                "rows": len(df),
                "columns": len(df.columns),
                "headers": df.columns.tolist(),
                "data": df.values.tolist()[:10]  # Preview first 10 rows
            }
            tables_data.append(table_dict)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "file_id": file_id,
                "tables_count": len(tables_data),
                "tables": tables_data
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")
