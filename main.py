from fastapi import FastAPI
from database.session import engine, Base
from routers import user, customer, sale, auth, address, treatment, saleStatistics, treatmentCategory
from fastapi.middleware.cors import CORSMiddleware
from core.config import ALLOWED_ORIGINS

app = FastAPI()

app.include_router(user.router)
app.include_router(customer.router)
app.include_router(sale.router)
app.include_router(saleStatistics.router)
app.include_router(auth.router)
app.include_router(address.router)
app.include_router(treatment.router)
app.include_router(treatmentCategory.router)

Base.metadata.create_all(bind=engine)

app.add_middleware(
  CORSMiddleware,
  allow_origins=ALLOWED_ORIGINS,
  allow_credentials=True,
  allow_methods=['*'],
  allow_headers=['*']
)