from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.session import SessionLocal, get_db
from models.sale import Sale, SaleTreatment
from schemas.sale import SaleCreate, SaleRead

router = APIRouter(prefix="/sales", tags=["sales"])

@router.post("/", response_model=SaleRead)
def create_sale(sale: SaleCreate, db: Session = Depends(get_db)):
    db_sale = Sale(
        user_id=sale.user_id,
        customer_id=sale.customer_id,
        sale_date=sale.sale_date,
        detail=sale.detail,
        payment_type=sale.payment_type,
        total_amount=sale.total_amount,
    )
    db.add(db_sale)
    db.commit()
    db.refresh(db_sale)

    # treatments 추가
    for treatment in sale.treatments:
        db_treatment = SaleTreatment(
            sale_id=db_sale.id,
            treatment_name=treatment.treatment_name,
            price=treatment.price,
        )
        db.add(db_treatment)
    db.commit()
    db.refresh(db_sale)

    return db_sale

@router.get("/", response_model=list[SaleRead])
def read_sales(db: Session = Depends(get_db)):
    return db.query(Sale).all()