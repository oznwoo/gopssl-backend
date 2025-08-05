from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Dict
from models.sale import Sale
from database.session import get_db

router = APIRouter(prefix="/sales", tags=["sales"])

@router.get("/summary/daily", response_model=Dict[str, int])
def get_daily_sales_summary(
    year: int = Query(..., ge=2000, le=2100, description="조회할 연도"),
    month: int = Query(..., ge=1, le=12, description="조회할 월"),
    db: Session = Depends(get_db)
):
    # 해당 연,월의 날짜별 매출 합계 조회
    results = (
        db.query(
            Sale.sale_date,
            func.coalesce(func.sum(Sale.total_amount), 0).label("total_amount")
        )
        .filter(
            extract("year", Sale.sale_date) == year,
            extract("month", Sale.sale_date) == month,
        )
        .group_by(Sale.sale_date)
        .all()
    )

    # 날짜를 키로, 총 매출을 값으로 하는 딕셔너리 생성 (YYYY-MM-DD 포맷)
    summary = {
        row.sale_date.strftime("%Y-%m-%d"): int(row.total_amount) for row in results
    }

    return summary
