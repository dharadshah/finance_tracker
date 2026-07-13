from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from finance_tracker.database import init_db
from finance_tracker.api.routers import accounts, transactions, categories, import_, rules, mutual_funds, stocks



@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Finance Tracker API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(import_.router)
app.include_router(rules.router)
app.include_router(mutual_funds.router)
app.include_router(stocks.router)

