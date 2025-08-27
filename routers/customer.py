from fastapi import APIRouter, Depends, HTTPException, Query
from schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, case, or_, literal_column
from typing import List
from database.session import SessionLocal, get_db
from models.customer import Customer
from models.sale import Sale
from models.user import User
from dependencies import get_current_user


router = APIRouter(prefix="/customers", tags=["customers"])

@router.post("/", response_model=CustomerRead)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 현재 로그인한 사용자만 고객 생성 가능하도록 검증
    if customer.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="자신의 고객만 생성할 수 있습니다.")
    
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
def read_customers(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # 현재 로그인한 사용자의 고객 조회
    customers = db.query(Customer).filter(Customer.user_id == current_user.id).all()

    result = []
    for customer in customers:
        # 가장 최근 판매 내역 가져오기
        latest_sale = (
            db.query(Sale)
            .filter(Sale.customer_id == customer.id)
            .order_by(Sale.created_at.desc())
            .first()
        )

        customer_data = CustomerRead.model_validate(customer)
        customer_data.num_of_visits = latest_sale.num_of_visits if latest_sale else None
        result.append(customer_data)

    return result


@router.get("/{customer_id}", response_model=CustomerRead)
def read_customers_by_Id(
    customer_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.user_id == current_user.id
    ).first()

    if not customer:
        raise HTTPException(status_code=404, detail="고객을 찾을 수 없습니다.")

    # 가장 최근 판매 내역 가져오기
    latest_sale = (
        db.query(Sale)
        .filter(Sale.customer_id == customer.id)
        .order_by(Sale.created_at.desc())
        .first()
    )

    customer_data = CustomerRead.model_validate(customer)
    customer_data.num_of_visits = latest_sale.num_of_visits if latest_sale else None

    return customer_data


# Update
@router.put("/{customer_id}", response_model=CustomerRead)
def update_user(customer_id: int, updated_data: CustomerCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.user_id == current_user.id
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="고객을 찾을 수 없습니다.")

    # 현재 로그인한 사용자만 고객 수정 가능하도록 검증
    if updated_data.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="자신의 고객만 수정할 수 있습니다.")

    for key, value in updated_data.dict(exclude_unset=True).items():
        setattr(customer, key, value)

    db.commit()
    db.refresh(customer)
    return customer


# Delete
@router.delete("/{customer_id}")
def delete_user(customer_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.user_id == current_user.id
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="고객을 찾을 수 없습니다.")
    
    db.delete(customer)
    db.commit()
    return {"message": "고객이 삭제되었습니다."}