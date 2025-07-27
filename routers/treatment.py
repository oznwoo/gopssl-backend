from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database.session import get_db
from models.treatment import Treatment as TreatmentModel
from schemas.treatment import (
    Treatment,
    TreatmentCreate,
)

router = APIRouter(
    prefix="/treatments",
    tags=["treatments"],
)


@router.get("/", response_model=List[Treatment])
def get_all_treatments(db: Session = Depends(get_db)):
    return db.query(TreatmentModel).all()


@router.get("/{treatment_id}", response_model=Treatment)
def get_treatment(treatment_id: int, db: Session = Depends(get_db)):
    treatment = db.query(TreatmentModel).get(treatment_id)
    if not treatment:
        raise HTTPException(status_code=404, detail="Treatment not found")
    return treatment


@router.post("/", response_model=Treatment, status_code=status.HTTP_201_CREATED)
def create_treatment(treatment: TreatmentCreate, db: Session = Depends(get_db)):
    db_treatment = TreatmentModel(**treatment.dict())
    db.add(db_treatment)
    db.commit()
    db.refresh(db_treatment)
    return db_treatment



@router.delete("/{treatment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_treatment(treatment_id: int, db: Session = Depends(get_db)):
    treatment = db.query(TreatmentModel).get(treatment_id)
    if not treatment:
        raise HTTPException(status_code=404, detail="Treatment not found")

    db.delete(treatment)
    db.commit()