from fastapi import APIRouter, Depends, HTTPException, Query
from schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate, DeletedCustomerRead
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, case, or_, literal_column, and_
from typing import List
from datetime import datetime, timedelta, timezone
from database.session import SessionLocal, get_db
from models.customer import Customer
from models.sale import Sale
from models.user import User
from dependencies import get_current_user


router = APIRouter(prefix="/customers", tags=["customers"])

@router.post("/", response_model=CustomerRead)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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

@router.get("/", response_model=List[CustomerRead])
def read_customers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    customers = db.query(Customer).filter(
        Customer.user_id == current_user.id,
        Customer.is_deleted == False
    ).all()

    result = []
    for customer in customers:
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


@router.delete("/cleanup/inactive")
def cleanup_inactive_customers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """name='신규'이고 created_at 6개월 이상 지난 고객을 소프트 딜리트."""
    six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)

    targets = db.query(Customer).filter(
        Customer.name == "신규",
        Customer.created_at < six_months_ago,
        Customer.is_deleted == False,
        Customer.user_id == current_user.id
    ).all()

    now = datetime.now(timezone.utc)
    for customer in targets:
        customer.is_deleted = True
        customer.deleted_at = now

    db.commit()

    return {
        "deleted_count": len(targets),
        "deleted_customers": [
            {
                "id": c.id,
                "name": c.name,
                "detail": c.detail,
                "created_at": c.created_at.isoformat(),
                "deleted_at": now.isoformat(),
            }
            for c in targets
        ]
    }


@router.get("/deleted", response_model=List[DeletedCustomerRead])
def get_deleted_customers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """삭제된 고객 목록 — 설정 화면용. deleted_at 내림차순."""
    return db.query(Customer).filter(
        Customer.user_id == current_user.id,
        Customer.is_deleted == True
    ).order_by(Customer.deleted_at.desc()).all()


@router.post("/{customer_id}/restore")
def restore_customer(
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
    if not customer.is_deleted:
        raise HTTPException(status_code=400, detail="삭제된 고객이 아닙니다.")

    customer.is_deleted = False
    customer.deleted_at = None
    db.commit()

    return {"message": "고객이 복구되었습니다."}


@router.delete("/{customer_id}/permanent")
def permanent_delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """영구 삭제 — 실제 DB에서 제거. 연결된 Sale의 customer_id는 SET NULL로 유지됨."""
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.user_id == current_user.id
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="고객을 찾을 수 없습니다.")

    db.delete(customer)
    db.commit()

    return {"message": "고객이 영구 삭제되었습니다."}


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

    latest_sale = (
        db.query(Sale)
        .filter(Sale.customer_id == customer.id)
        .order_by(Sale.created_at.desc())
        .first()
    )

    customer_data = CustomerRead.model_validate(customer)
    customer_data.num_of_visits = latest_sale.num_of_visits if latest_sale else None

    return customer_data


@router.put("/{customer_id}", response_model=CustomerRead)
def update_user(customer_id: int, updated_data: CustomerCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.user_id == current_user.id,
        Customer.is_deleted == False
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="고객을 찾을 수 없습니다.")

    if updated_data.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="자신의 고객만 수정할 수 있습니다.")

    for key, value in updated_data.dict(exclude_unset=True).items():
        setattr(customer, key, value)

    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}")
def delete_customer(
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

    customer.is_deleted = True
    customer.deleted_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": "고객이 삭제되었습니다."}
