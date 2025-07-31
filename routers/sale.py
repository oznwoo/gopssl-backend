from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database.session import get_db
from models.sale import Sale, SaleTreatment
from models.treatment import Treatment  # treatment 관계용
from schemas.sale import SaleCreate, SaleRead
from datetime import datetime, time, timedelta
from typing import Optional

router = APIRouter(prefix="/sales", tags=["sales"])

@router.post("/", response_model=SaleRead)
def create_sale(sale: SaleCreate, db: Session = Depends(get_db)):
    # 날짜 문자열이나 date 객체를 datetime으로 변환하며 시간 포함 처리
    input_date = sale.sale_date
    if isinstance(input_date, str):
        sale_date_only = datetime.strptime(input_date, "%Y-%m-%d").date()
    else:
        sale_date_only = input_date  # date 타입으로 가정

    today = datetime.now().date()

    if sale_date_only == today:
        sale_date_with_time = datetime.now()
    else:
        sale_date_with_time = datetime.combine(sale_date_only, time.min)

    db_sale = Sale(
        user_id=sale.user_id,
        customer_id=sale.customer_id,
        sale_date=sale_date_with_time,  # datetime 넣기
        detail=sale.detail,
        payment_type=sale.payment_type,
        total_amount=sale.total_amount,
    )
    db.add(db_sale)
    db.commit()
    db.refresh(db_sale)

    # treatments 추가
    for treatment_data in sale.treatments:
        treatment = db.query(Treatment).get(treatment_data.treatment_id)
        if not treatment:
            raise HTTPException(
                status_code=404,
                detail=f"Treatment ID {treatment_data.treatment_id} not found"
            )

        db_treatment = SaleTreatment(
            sale_id=db_sale.id,
            treatment_id=treatment_data.treatment_id,
            price=treatment_data.price,
        )
        db.add(db_treatment)

    db.commit()
    db.refresh(db_sale)
    return db_sale


@router.get("/", response_model=list[SaleRead])
def read_sales(db: Session = Depends(get_db)):
    return db.query(Sale).all()

@router.get("/by_date", response_model=list[SaleRead])
def read_sales_by_date(
    date: Optional[str] = Query(None, description="조회할 날짜 (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    if not date:
        raise HTTPException(status_code=400, detail="date query parameter is required")

    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())

    sales = (
        db.query(Sale)
        .filter(Sale.sale_date >= start_dt, Sale.sale_date <= end_dt)
        .all()
    )
    return sales