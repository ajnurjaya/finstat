"""
Logs API - View query logs and statistics
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional

from app.utils.query_logger import get_query_logger

router = APIRouter()


@router.get("/logs/recent")
async def get_recent_logs(limit: int = Query(10, ge=1, le=100)):
    """
    Get recent query logs

    Args:
        limit: Number of recent logs to return (1-100, default 10)
    """
    try:
        logger = get_query_logger()
        logs = logger.get_recent_logs(limit=limit)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "count": len(logs),
                "logs": logs
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")


@router.get("/logs/search")
async def search_logs(
    question: Optional[str] = None,
    file_id: Optional[str] = None,
    min_response_time: Optional[float] = None,
    date: Optional[str] = None
):
    """
    Search logs with filters

    Args:
        question: Filter by question content (partial match)
        file_id: Filter by specific file ID
        min_response_time: Filter by minimum response time in ms
        date: Filter by specific date (format: YYYY-MM-DD)
    """
    try:
        logger = get_query_logger()
        logs = logger.search_logs(
            question_contains=question,
            file_id=file_id,
            min_response_time=min_response_time,
            date=date
        )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "count": len(logs),
                "filters": {
                    "question": question,
                    "file_id": file_id,
                    "min_response_time": min_response_time,
                    "date": date
                },
                "logs": logs
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search logs: {str(e)}")


@router.get("/logs/statistics")
async def get_statistics(date: Optional[str] = None):
    """
    Get statistics for logged queries

    Args:
        date: Optional specific date (format: YYYY-MM-DD), defaults to today
    """
    try:
        logger = get_query_logger()
        stats = logger.get_statistics(date=date)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "date": date or "today",
                "statistics": stats
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")