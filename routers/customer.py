from fastapi import APIRouter, Depends, HTTPException
from schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from sqlalchemy.orm import Session
from database.session import SessionLocal, get_db
from models.customer import Customer


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