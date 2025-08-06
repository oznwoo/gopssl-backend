from fastapi import APIRouter, Depends, HTTPException, Query
from schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, case, or_, literal_column
from typing import List
from database.session import SessionLocal, get_db
from models.customer import Customer
from models.sale import Sale


router = APIRouter(prefix="/customers", tags=["customers"])

@router.post("/", response_model=CustomerRead)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
  new_customer = Customer(
     user_id=customer.user_id,
     name=customer.name,
     phone_number=customer.phone_number,
     detail=customer.detail
  )
  db.add(new_customer)
  db.commit()
  db.refresh(new_customer)
  return new_customer

@router.get("/", response_model=list[CustomerRead])
def read_customers(db: Session = Depends(get_db)):
    return db.query(Customer).all()



@router.get("/search", response_model=list[CustomerRead])
def read_customers_by_name(
    name: str = Query(..., description="고객 이름 또는 상세 정보 (부분 검색)"),
    db: Session = Depends(get_db)
):
    keyword = f"%{name}%"

    # 1. name 필드에서 검색된 고객 (우선순위 높음)
    name_matches = (
        db.query(Customer)
        .filter(Customer.name.ilike(keyword))
        .all()
    )

    detail_matches = []
    # detail 검색은 검색어가 2글자 이상일 때만 수행
    if len(name.strip()) >= 2:
        detail_matches = (
            db.query(Customer)
            .filter(
                Customer.detail.isnot(None),
                Customer.detail.ilike(keyword),
                ~Customer.id.in_([c.id for c in name_matches])  # name에 이미 포함된 것은 제외
            )
            .all()
        )

    # 결과 합치기: name > detail 순서로
    customers = name_matches + detail_matches

    if not customers:
        raise HTTPException(status_code=404, detail="고객을 찾을 수 없습니다.")

    result = []
    for customer in customers:
        latest_sale = (
            db.query(Sale)
            .filter(Sale.customer_id == customer.id)
            .order_by(Sale.created_at.desc())
            .first()
        )

        customer_data = CustomerRead.from_orm(customer)
        customer_data.num_of_visits = latest_sale.num_of_visits if latest_sale else None
        result.append(customer_data)

    return result


@router.get("/{customer_id}", response_model=CustomerRead)
def read_customers_by_Id(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
      raise HTTPException(status_code=404, detail="고객을 찾을 수 없습니다.")
    return customer

# Update
@router.put("/{customer_id}", response_model=CustomerRead)
def update_user(customer_id: int, updated_data: CustomerCreate, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="고객을 찾을 수 없습니다.")

    for key, value in updated_data.dict(exclude_unset=True).items():
        setattr(customer, key, value)

    db.commit()
    db.refresh(customer)
    return customer


# Delete
@router.delete("/{customer_id}")
def delete_user(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="고객을 찾을 수 없습니다.")
    
    db.delete(customer)
    db.commit()
    return {"message": "고객이 삭제되었습니다."}