from fastapi import APIRouter, Depends, HTTPException
from schemas.customer import CustomerCreate, CustomerRead
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