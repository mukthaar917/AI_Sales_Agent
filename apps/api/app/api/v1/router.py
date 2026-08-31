from fastapi import APIRouter

from app.api.v1 import (
    auth,
    customers,
    products,
    quotations,
    system,
)
from app.api.v1.endpoints import email, gmail


api_router = APIRouter()


api_router.include_router(
    system.router,
    prefix="/system",
    tags=["System"],
)

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

api_router.include_router(
    customers.router,
    prefix="/customers",
    tags=["Customers"],
)

api_router.include_router(
    products.router,
    prefix="/products",
    tags=["Products"],
)

api_router.include_router(
    quotations.router,
    prefix="/quotations",
    tags=["Quotations"],
)

api_router.include_router(
    gmail.router,
    prefix="/gmail",
    tags=["Gmail"],
)

api_router.include_router(
    email.router,
    prefix="/email",
    tags=["Email"],
)