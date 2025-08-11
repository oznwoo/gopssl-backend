from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import extract, func, and_
from typing import Dict, List
from models.sale import Sale
from database.session import get_db
from datetime import datetime, date, timedelta
from collections import defaultdict

router = APIRouter(prefix="/sales/statistics", tags=["sales"])

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

@router.get("/summary/monthly")
def get_sales_summary(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db)
):
    today = date.today()
    input_date = date(year, month, 1)
    is_current_month = today.year == year and today.month == month
    is_current_year = today.year == year

    ### 1. 매출 유형 (payment_type 비율)
    sales_in_month = (
        db.query(Sale.payment_type, func.sum(Sale.total_amount).label("total"))
        .filter(
            extract("year", Sale.sale_date) == year,
            extract("month", Sale.sale_date) == month,
        )
        .group_by(Sale.payment_type)
        .all()
    )

    total_sum = sum(row.total for row in sales_in_month)
    payment_type_ratio = {}
    for row in sales_in_month:
        if row.payment_type:
            payment_type_ratio[row.payment_type.lower()] = round(row.total / total_sum, 2)

    ### 2. 월별 비교 (최근 4개월)
    monthly_comparison = []
    for i in range(3, -1, -1):
        target_date = date(year, month, 1)
        month_shift = (target_date.month - i - 1) % 12 + 1
        year_shift = target_date.year + (target_date.month - i - 1) // 12
        target_start = date(year_shift, month_shift, 1)

        if month_shift == 12:
            next_month = date(year_shift + 1, 1, 1)
        else:
            next_month = date(year_shift, month_shift + 1, 1)

        if year_shift == today.year and month_shift == today.month:
            target_end = today + timedelta(days=1)  # ✅ 오늘 포함
        else:
            target_end = next_month

        total = (
            db.query(func.sum(Sale.total_amount))
            .filter(and_(
                Sale.sale_date >= target_start,
                Sale.sale_date < target_end
            ))
            .scalar()
        ) or 0

        monthly_comparison.append({
            "year": year_shift,
            "month": month_shift,
            "total": int(total)
        })

    ### 3. 연도별 비교
    yearly_comparison = defaultdict(lambda: [0]*12)
    years = [year - 1, year] if not is_current_year else [year - 1, year]

    for y in years:
        for m in range(1, 13):
            if y == today.year and m > today.month:
                continue  # 현재 연도는 이번 달까지만
            start = date(y, m, 1)
            if m == 12:
                end = date(y + 1, 1, 1)
            else:
                end = date(y, m + 1, 1)

            total = (
                db.query(func.sum(Sale.total_amount))
                .filter(and_(
                    Sale.sale_date >= start,
                    Sale.sale_date < end
                ))
                .scalar()
            ) or 0

            yearly_comparison[str(y)][m - 1] = int(total)

    return {
        "monthly_comparison": monthly_comparison,
        "yearly_comparison": yearly_comparison,
        "payment_type_ratio": payment_type_ratio,
    }
