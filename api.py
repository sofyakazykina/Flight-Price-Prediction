"""Flight Price Analysis — REST API (FastAPI)
Run: uvicorn api:app --reload
Docs: http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field
from typing import Optional, Literal
import pandas as pd
import math

app = FastAPI(
    title="Flight Price Analysis API",
    description="REST API for exploring Indian domestic flight prices.",
    version="1.0.0",
)

# ── Load data with cleaning ──────────────────────────────────────────────────

def load_df() -> pd.DataFrame:
    df = pd.read_csv("Clean_Dataset.csv", index_col=0)
    
    # Добавляем производные колонки
    df["num_stops"] = df["stops"].map({"zero": 0, "one": 1, "two_or_more": 2})
    df["price_per_hour"] = (df["price"] / df["duration"]).round(2)
    df["is_early_booking"] = (df["days_left"] > 30).astype(int)
    
    # Очистка от NaN и inf
    numeric_cols = ["duration", "days_left", "price", "num_stops", "price_per_hour", "is_early_booking"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    string_cols = ["airline", "source_city", "destination_city", "departure_time", "arrival_time", "stops", "class"]
    for col in string_cols:
        df[col] = df[col].fillna('').astype(str)
    
    return df

_records: list[dict] = load_df().to_dict(orient="records")

def get_df() -> pd.DataFrame:
    """Возвращает чистый DataFrame без NaN и с правильными типами."""
    df = pd.DataFrame(_records)
    
    # Принудительно приводим числовые колонки
    numeric_cols = ["duration", "days_left", "price", "num_stops", "price_per_hour", "is_early_booking"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0
    
    # Приводим строковые колонки
    string_cols = ["airline", "source_city", "destination_city", "departure_time", "arrival_time", "stops", "class"]
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].fillna('').astype(str)
        else:
            df[col] = ''
    
    return df

# ── Models ─────────────────────────────────────────────────────────────────────

class FlightCreate(BaseModel):
    airline: str = Field(..., json_schema_extra={"example": "IndiGo"})
    source_city: str = Field(..., json_schema_extra={"example": "Delhi"})
    destination_city: str = Field(..., json_schema_extra={"example": "Mumbai"})
    departure_time: Literal["Early_Morning","Morning","Afternoon","Evening","Night","Late_Night"]
    arrival_time: Literal["Early_Morning","Morning","Afternoon","Evening","Night","Late_Night"]
    stops: Literal["zero","one","two_or_more"]
    flight_class: Literal["Economy","Business"] = Field(..., alias="class")
    duration: float = Field(..., gt=0, json_schema_extra={"example": 2.5})
    days_left: int = Field(..., ge=1, le=49, json_schema_extra={"example": 15})
    price: float = Field(..., gt=0, json_schema_extra={"example": 5500.0})

    model_config = {"populate_by_name": True}

# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    df = get_df()
    return {
        "status": "ok",
        "total_records": len(df),
        "airlines": sorted(df["airline"].unique().tolist()),
        "cities": sorted(df["source_city"].unique().tolist()),
        "docs": "/docs",
    }

@app.get("/flights")
def get_flights(
    airline: Optional[str] = Query(None),
    flight_class: Optional[Literal["Economy","Business"]] = Query(None, alias="class"),
    source_city: Optional[str] = Query(None),
    destination_city: Optional[str] = Query(None),
    price_min: Optional[float] = Query(None, ge=0),
    price_max: Optional[float] = Query(None, ge=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500000),
):
    df = get_df()
    
    if airline:
        df = df[df["airline"].str.lower() == airline.lower()]
    if flight_class:
        df = df[df["class"].str.lower() == flight_class.lower()]
    if source_city:
        df = df[df["source_city"].str.lower() == source_city.lower()]
    if destination_city:
        df = df[df["destination_city"].str.lower() == destination_city.lower()]
    if price_min is not None:
        df = df[df["price"] >= price_min]
    if price_max is not None:
        df = df[df["price"] <= price_max]
    
    total = len(df)
    page = df.iloc[skip: skip + limit]
    
    # Заменяем NaN и inf на None, чтобы JSON был валидным
    records = page.replace({float('nan'): None, float('inf'): None, -float('inf'): None}).to_dict(orient="records")
    
    return {
        "total_matching": total,
        "returned": len(page),
        "flights": records,
    }

@app.post("/flights", status_code=201)
def create_flight(flight: FlightCreate):
    # Получаем данные с правильными алиасами
    data = flight.model_dump(by_alias=True)
    
    # Добавляем производные поля
    stops_map = {"zero": 0, "one": 1, "two_or_more": 2}
    data["num_stops"] = stops_map[data["stops"]]
    data["price_per_hour"] = round(data["price"] / data["duration"], 2)
    data["is_early_booking"] = 1 if data["days_left"] > 30 else 0
    
    # Убеждаемся, что все строковые поля — это строки
    for key in ["airline", "source_city", "destination_city", "departure_time", "arrival_time", "stops", "class"]:
        if key in data:
            data[key] = str(data[key])
    
    _records.append(data)
    
    return {
        "message": "Flight added successfully.",
        "total_records": len(_records),
        "new_record": data,
    }