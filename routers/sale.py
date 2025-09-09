from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from database.session import get_db
from models.sale import Sale, SaleTreatment
from models.treatment import Treatment  # treatment 관계용
from models.customer import Customer
from models.user import User
from schemas.sale import SaleCreate, SaleRead, SaleTreatmentRead, SaleUpdate
from dependencies import get_current_user
from datetime import datetime, time
from typing import Optional, List

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("/", response_model=SaleRead)
def create_sale(sale: SaleCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 현재 로그인한 사용자만 매출 생성 가능하도록 검증
    if sale.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="자신의 매출만 생성할 수 있습니다.")

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
        },
        from_attributes=True
    )

    return sale_read

@router.get("/", response_model=list[SaleRead])
def read_sales(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Sale).filter(Sale.user_id == current_user.id).all()

@router.get("/by_date", response_model=List[SaleRead])
def read_sales_by_date(
    date: Optional[str] = Query(None, description="조회할 날짜 (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        .filter(Sale.user_id == current_user.id)
        .options(
            joinedload(Sale.customer),
            joinedload(Sale.treatments).joinedload(SaleTreatment.treatment)
        )
        .all()
    )

    sale_read_list = []
    for sale in sales:

        
        sale_dict = jsonable_encoder(sale)
        sale_dict["customer_name"] = sale.customer.name if sale.customer else "알 수 없음"
        sale_dict["num_of_visits"] = sale.num_of_visits

        sale_dict["treatments"] = [
            SaleTreatmentRead(
                id=st.id,
                sale_id=st.sale_id,
                treatment_id=st.treatment_id,
                treatment_name=st.treatment.name if st.treatment else None,
                price=st.price,
                treatment_category=st.treatment.category
            )
            for st in sale.treatments
        ]

        sale_read_list.append(SaleRead(**sale_dict))

    return sale_read_list

@router.get("/{sale_id}", response_model=SaleRead)
def read_sales_by_id(sale_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sale = (
        db.query(Sale)
        .filter(Sale.id == sale_id)
        .filter(Sale.user_id == current_user.id)
        .options(
            joinedload(Sale.customer),
            joinedload(Sale.treatments).joinedload(SaleTreatment.treatment)
        )
        .first()
    )
    if not sale:
        raise HTTPException(status_code=404, detail="매출 정보를 찾을 수 없습니다.")


    sale_dict = jsonable_encoder(sale)
    sale_dict["customer_name"] = sale.customer.name if sale.customer else "알 수 없음"
    sale_dict["num_of_visits"] = sale.num_of_visits
    sale_dict["treatments"] = [
        {
            "id": st.id,
            "sale_id": st.sale_id,
            "treatment_id": st.treatment_id,
            "treatment_name": st.treatment.name if st.treatment else None,
            "price": st.price
        }
        for st in sale.treatments
    ]

    return SaleRead(**sale_dict)


# 고객별 전체 매출 조회
@router.get("/by_customer/{customer_id}", response_model=List[SaleRead])
def read_sales_by_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 고객 존재 여부 체크
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.user_id == current_user.id)
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="고객 정보를 찾을 수 없습니다.")

    # 해당 고객의 모든 매출 조회
    sales = (
        db.query(Sale)
        .filter(Sale.customer_id == customer_id, Sale.user_id == current_user.id)
        .options(
            joinedload(Sale.customer),
            joinedload(Sale.treatments).joinedload(SaleTreatment.treatment),
        )
        .order_by(Sale.sale_date.asc())
        .all()
    )

    sale_read_list = []
    for sale in sales:
        sale_dict = jsonable_encoder(sale)

        sale_dict["customer_name"] = sale.customer.name if sale.customer else "알 수 없음"
        sale_dict["num_of_visits"] = sale.num_of_visits   # ✅ 해당 매출 당시 회차 그대로 사용
        sale_dict["treatments"] = [
            SaleTreatmentRead(
                id=st.id,
                sale_id=st.sale_id,
                treatment_id=st.treatment_id,
                treatment_name=st.treatment.name if st.treatment else None,
                price=st.price,
            )
            for st in sale.treatments
        ]
        sale_read_list.append(SaleRead(**sale_dict))

    return sale_read_list


# Update
@router.put("/", response_model=SaleRead)
def update_sale(sale: SaleUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 기존 매출 조회 (id 기준)
    existing_sale = db.query(Sale).filter(Sale.id == sale.id).first()
    if not existing_sale:
        raise HTTPException(status_code=404, detail="매출이 존재하지 않습니다.")

    # 현재 로그인한 사용자만 매출 수정 가능하도록 검증
    if existing_sale.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="자신의 매출만 수정할 수 있습니다.")

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

    # --- 방문 회차 계산 처리 ---

    # 고객 아이디가 바뀌었는지 확인
    customer_id_changed = existing_sale.customer_id != sale.customer_id

    # 사용자 ID가 바뀌었는지 확인 (보안상 허용하지 않음)
    if sale.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="자신의 매출만 수정할 수 있습니다.")

    # 기존 고객 방문수 -1 (기존 고객이 있다면)
    if customer_id_changed:
        # 기존 고객 방문수 업데이트 (기존 방문수 -1)
        prev_count = (
            db.query(func.count(Sale.id))
            .filter(Sale.customer_id == existing_sale.customer_id)
            .scalar()
        )
        if prev_count and prev_count > 0:
            # num_of_visits 필드가 과거에 저장되어 있으면 업데이트하는 등 필요 시 추가 작업 가능

            # 예: 기존 방문수에서 직접 빼는 것이 아니라, null로 처리하거나 실제 로직에 따라 조절 가능

            # 여기서는 별도의 작업 없이 유지하되, 후속 저장 때 새 고객 방문수를 올림

            pass

        # 새로운 고객 방문수 계산 (기존 방문 수 +1)
        visit_count = (
            db.query(func.count(Sale.id))
            .filter(Sale.customer_id == sale.customer_id)
            .scalar()
        )
        current_visit_number = visit_count + 1
    else:
        # 고객이 바뀌지 않으면 기존 방문수 유지
        current_visit_number = existing_sale.num_of_visits


    # 기존 매출 데이터 업데이트
    existing_sale.user_id = sale.user_id
    existing_sale.customer_id = sale.customer_id
    existing_sale.sale_date = sale_date_with_time
    existing_sale.detail = sale.detail
    existing_sale.payment_type = sale.payment_type
    existing_sale.total_amount = sale.total_amount
    existing_sale.extra_prices = sale.extra_prices
    existing_sale.num_of_visits = current_visit_number

    db.commit()

    # 기존 시술 모두 삭제 (Update 시 교체 처리)
    db.query(SaleTreatment).filter(SaleTreatment.sale_id == existing_sale.id).delete()
    db.commit()

    # 새 시술 추가
    for treatment_data in sale.treatments:
        treatment = db.query(Treatment).get(treatment_data.treatment_id)
        if not treatment:
            raise HTTPException(
                status_code=404,
                detail=f"Treatment ID {treatment_data.treatment_id} not found"
            )
        db_treatment = SaleTreatment(
            sale_id=existing_sale.id,
            treatment_id=treatment_data.treatment_id,
            price=treatment_data.price,
        )
        db.add(db_treatment)
    db.commit()

    # 시술 목록 조회 (treatment_name 포함)
    db_treatments = (
        db.query(SaleTreatment)
        .filter(SaleTreatment.sale_id == existing_sale.id)
        .join(SaleTreatment.treatment)
        .all()
    )

    # 고객 이름 조회
    customer = db.query(Customer).get(existing_sale.customer_id)
    customer_name = customer.name if customer else "알 수 없음"

    # 응답객체 구성
    sale_read = SaleRead.model_validate(
        {
            **existing_sale.__dict__,
            "treatments": [
                SaleTreatmentRead(
                    id=st.id,
                    sale_id=st.sale_id,
                    treatment_id=st.treatment_id,
                    treatment_name=st.treatment.name if st.treatment else "알 수 없음",
                    price=st.price,
                )
                for st in db_treatments
            ],
            "customer_name": customer_name,
            "num_of_visits": current_visit_number,
        },
        from_attributes=True,
    )

    return sale_read


# Delete
@router.delete("/{sale_id}", response_model=dict)
def delete_sale(sale_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="매출 정보를 찾을 수 없습니다.")

    # 현재 로그인한 사용자만 매출 삭제 가능하도록 검증
    if sale.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="자신의 매출만 삭제할 수 있습니다.")

    # 관련 SaleTreatment 레코드들도 삭제(외래키 설정에 따라 자동 삭제될 수도 있음)
    db.query(SaleTreatment).filter(SaleTreatment.sale_id == sale_id).delete()

    db.delete(sale)
    db.commit()

    return {"message": "매출 정보가 삭제되었습니다."}
