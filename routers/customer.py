from fastapi import APIRouter, Depends, HTTPException
from schemas.customer import CustomerCreate, CustomerRead
from sqlalchemy.orm import Session
from database.session import SessionLocal, get_db
from models.customer import Customer


router = APIRouter(prefix="/customers", tags=["customers"])

@router.post("/", response_model=CustomerRead)
def create_customer(customer: CustomerRead, db: Session = Depends(get_db)):
  db_customer = Customer(**customer.dict())
  db.add(db_customer)
  db.commit()
  db.refresh(db_customer)
  return db_customer

@router.get("/", response_model=list[CustomerRead])
def read_customers(db: Session = Depends(get_db)):
    return db.query(Customer).all()