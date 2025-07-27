from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.session import get_db
from models.sale import Sale, SaleTreatment
from models.treatment import Treatment  # treatment 관계용
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
    for treatment_data in sale.treatments:
        # Treatment 유효성 확인 (optional but good practice)
        treatment = db.query(Treatment).get(treatment_data.treatment_id)
        if not treatment:
            raise HTTPException(status_code=404, detail=f"Treatment {treatment_data.treatment_id} not found")

        db_treatment = SaleTreatment(
            sale_id=db_sale.id,
            treatment_id=treatment_data.treatment_id,
            price=treatment_data.price,
        )
        db.add(db_treatment)

    db.commit()

    # nested 관계 포함 응답을 위해 다시 쿼리
    db_sale = db.query(Sale).filter(Sale.id == db_sale.id).first()

    return db_sale


@router.get("/", response_model=list[SaleRead])
def read_sales(db: Session = Depends(get_db)):
    return db.query(Sale).all()