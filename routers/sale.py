from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from database.session import get_db
from models.sale import Sale, SaleTreatment
from models.treatment import Treatment  # treatment 관계용
from models.customer import Customer
from schemas.sale import SaleCreate, SaleRead, SaleTreatmentRead
from datetime import datetime, time
from typing import Optional, List

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("/", response_model=SaleRead)
def create_sale(sale: SaleCreate, db: Session = Depends(get_db)):
    # 날짜 파싱
    input_date = sale.sale_date
    if isinstance(input_date, str):
        sale_date_only = datetime.strptime(input_date, "%Y-%m-%d").date()
    else:
        sale_date_only = input_date

    today = datetime.now().date()
    if sale_date_only == today:
        sale_date_with_time = datetime.now()
    else:
        sale_date_with_time = datetime.combine(sale_date_only, time.min)

    # 👉 방문 회차 계산 (기존 방문 수 + 1)
    visit_count = (
        db.query(func.count(Sale.id))
        .filter(Sale.customer_id == sale.customer_id)
        .scalar()
    )
    current_visit_number = visit_count + 1

    # 최초/최신 방문일 계산
    first_visit = (
        db.query(
            func.min(Sale.sale_date))
        .filter(Sale.customer_id == sale.customer_id)
        .one()
    )
    # 이전 방문일 구하기 (현재 방문일 제외한 가장 최근 방문일)
    previous_visit = (
        db.query(func.max(Sale.sale_date))
        .filter(
            Sale.customer_id == sale.customer_id,
            Sale.sale_date < sale_date_with_time  # 핵심: 현재 방문일보다 이전만
        )
        .scalar()
    )

    # 매출 생성
    db_sale = Sale(
        user_id=sale.user_id,
        customer_id=sale.customer_id,
        sale_date=sale_date_with_time,
        detail=sale.detail,
        payment_type=sale.payment_type,
        total_amount=sale.total_amount,
        extra_prices=sale.extra_prices,
        num_of_visits=current_visit_number,  # ✅ 저장
    )
    db.add(db_sale)
    db.commit()
    db.refresh(db_sale)

    # 시술 추가
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

    # 시술 목록 조회 (treatment_name 포함시키기 위해 join)
    db_treatments = (
        db.query(SaleTreatment)
        .filter(SaleTreatment.sale_id == db_sale.id)
        .join(SaleTreatment.treatment)
        .all()
    )

    # 고객 이름 조회
    customer = db.query(Customer).get(sale.customer_id)
    customer_name = customer.name if customer else "알 수 없음"

    # 응답 객체 구성
    sale_read = SaleRead.model_validate(
        {
            **db_sale.__dict__,
            "treatments": [
                SaleTreatmentRead(
                    id=st.id,
                    sale_id=st.sale_id,
                    treatment_id=st.treatment_id,
                    treatment_name=st.treatment.name if st.treatment else "알 수 없음",
                    price=st.price
                )
                for st in db_treatments
            ],
            "customer_name": customer_name,
            "num_of_visits": current_visit_number,
            "first_visit": first_visit,
            "previous_visit": previous_visit,
        },
        from_attributes=True
    )

    return sale_read

@router.get("/", response_model=list[SaleRead])
def read_sales(db: Session = Depends(get_db)):
    return db.query(Sale).all()

@router.get("/by_date", response_model=List[SaleRead])
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

    sales = (
        db.query(Sale)
        .filter(Sale.sale_date == target_date)
        .options(
            joinedload(Sale.customer),
            joinedload(Sale.treatments).joinedload(SaleTreatment.treatment)
        )
        .all()
    )

    sale_read_list = []
    for sale in sales:
        # 방문일 범위 계산
        first_visit = (
            db.query(func.min(Sale.sale_date))
            .filter(Sale.customer_id == sale.customer_id)
            .scalar()
        )

        # 이번 sale 제외, 가장 최근 방문일
        previous_visit = (
            db.query(func.max(Sale.sale_date))
            .filter(
                Sale.customer_id == sale.customer_id,
                Sale.sale_date < sale.sale_date  # 현재 sale 날짜보다 이전
            )
            .scalar()
        )
        
        sale_dict = jsonable_encoder(sale)
        sale_dict["customer_name"] = sale.customer.name if sale.customer else "알 수 없음"
        sale_dict["num_of_visits"] = sale.num_of_visits
        sale_dict["first_visit"] = first_visit
        sale_dict["previous_visit"] = previous_visit

        sale_dict["treatments"] = [
            SaleTreatmentRead(
                id=st.id,
                sale_id=st.sale_id,
                treatment_id=st.treatment_id,
                treatment_name=st.treatment.name if st.treatment else None,
                price=st.price
            )
            for st in sale.treatments
        ]

        sale_read_list.append(SaleRead(**sale_dict))

    return sale_read_list