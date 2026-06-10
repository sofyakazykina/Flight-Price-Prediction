"""Flight Price Analysis — REST API (FastAPI)
Run: uvicorn api:app --reload
Docs: http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Literal
import pandas as pd

app = FastAPI(
    title="Flight Price Analysis API",
    description="REST API for exploring Indian domestic flight prices.",
    version="1.0.0",
)

# ── Load data ─────────────────────────────────────────────────────────────────

def load_df() -> pd.DataFrame:
    df = pd.read_csv("Clean_Dataset.csv", index_col=0)
    df["num_stops"] = df["stops"].map({"zero": 0, "one": 1, "two_or_more": 2})
    df["price_per_hour"] = (df["price"] / df["duration"]).round(2)
    df["is_early_booking"] = (df["days_left"] > 30).astype(int)
    return df

_records: list[dict] = load_df().to_dict(orient="records")

def get_df() -> pd.DataFrame:
    return pd.DataFrame(_records)

# ── Models ────────────────────────────────────────────────────────────────────

class FlightCreate(BaseModel):
    airline: str = Field(..., example="IndiGo")
    source_city: str = Field(..., example="Delhi")
    destination_city: str = Field(..., example="Mumbai")
    departure_time: Literal["Early_Morning","Morning","Afternoon","Evening","Night","Late_Night"]
    arrival_time:   Literal["Early_Morning","Morning","Afternoon","Evening","Night","Late_Night"]
    stops: Literal["zero", "one", "two_or_more"]
    flight_class: Literal["Economy", "Business"] = Field(..., alias="class")
    duration: float = Field(..., gt=0, example=2.5)
    days_left: int  = Field(..., ge=1, le=49, example=15)
    price: float    = Field(..., gt=0, example=5500.0)

    model_config = {"populate_by_name": True}


class StatsOut(BaseModel):
    column: str
    mean: float; median: float; std: float; min: float; max: float; count: int

# ── Filter helper ─────────────────────────────────────────────────────────────

def apply_filters(df, airline, flight_class, source_city, destination_city,
                  stops, price_min, price_max, days_left_min, days_left_max):
    if airline:         df = df[df["airline"].str.lower() == airline.lower()]
    if flight_class:    df = df[df["class"].str.lower() == flight_class.lower()]
    if source_city:     df = df[df["source_city"].str.lower() == source_city.lower()]
    if destination_city: df = df[df["destination_city"].str.lower() == destination_city.lower()]
    if stops is not None:  df = df[df["num_stops"] == stops]
    if price_min:       df = df[df["price"] >= price_min]
    if price_max:       df = df[df["price"] <= price_max]
    if days_left_min:   df = df[df["days_left"] >= days_left_min]
    if days_left_max:   df = df[df["days_left"] <= days_left_max]
    return df

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["General"])
def root():
    df = get_df()
    return {
        "status": "ok",
        "total_records": len(df),
        "airlines": sorted(df["airline"].unique().tolist()),
        "cities":   sorted(df["source_city"].unique().tolist()),
        "docs": "/docs",
    }


@app.get("/flights", tags=["Flights"])
def get_flights(
    airline:          Optional[str]   = Query(None),
    flight_class:     Optional[Literal["Economy","Business"]] = Query(None, alias="class"),
    source_city:      Optional[str]   = Query(None),
    destination_city: Optional[str]   = Query(None),
    stops:            Optional[int]   = Query(None, ge=0, le=2),
    price_min:        Optional[float] = Query(None, ge=0),
    price_max:        Optional[float] = Query(None, ge=0),
    days_left_min:    Optional[int]   = Query(None, ge=1),
    days_left_max:    Optional[int]   = Query(None, le=49),
    skip:  int = Query(0,  ge=0, description="Offset for pagination"),
    limit: int = Query(20, ge=1, le=500000, description="Records per page"),
    sort_by:    Literal["price","duration","days_left"] = Query("price"),
    sort_order: Literal["asc","desc"] = Query("asc"),
):
    df = get_df()
    df = apply_filters(df, airline, flight_class, source_city, destination_city,
                       stops, price_min, price_max, days_left_min, days_left_max)
    df = df.sort_values(sort_by, ascending=(sort_order == "asc"))
    total = len(df)
    page  = df.iloc[skip: skip + limit]
    return {"total_matching": total, "skip": skip, "limit": limit,
            "returned": len(page), "flights": page.to_dict(orient="records")}


@app.get("/flights/stats", response_model=list[StatsOut], tags=["Statistics"])
def get_stats(
    airline:          Optional[str] = Query(None),
    flight_class:     Optional[Literal["Economy","Business"]] = Query(None, alias="class"),
    source_city:      Optional[str] = Query(None),
    destination_city: Optional[str] = Query(None),
):
    df = get_df()
    df = apply_filters(df, airline, flight_class, source_city, destination_city,
                       None, None, None, None, None)
    if df.empty:
        raise HTTPException(404, "No flights match the given filters.")
    return [
        StatsOut(column=col, mean=round(df[col].mean(),2), median=round(df[col].median(),2),
                 std=round(df[col].std(),2), min=round(df[col].min(),2),
                 max=round(df[col].max(),2), count=int(df[col].count()))
        for col in ["price","duration","days_left","num_stops"]
    ]


@app.get("/flights/airlines", tags=["Statistics"])
def get_airlines():
    df = get_df()
    result = []
    for airline in sorted(df["airline"].unique()):
        sub = df[df["airline"] == airline]
        eco = sub[sub["class"] == "Economy"]["price"]
        biz = sub[sub["class"] == "Business"]["price"]
        result.append({
            "airline": airline,
            "total_flights": len(sub),
            "economy_median_price": round(eco.median(), 0) if len(eco) else None,
            "business_median_price": round(biz.median(), 0) if len(biz) else None,
        })
    return result


@app.get("/flights/{flight_id}", tags=["Flights"])
def get_flight_by_id(flight_id: int):
    if flight_id < 0 or flight_id >= len(_records):
        raise HTTPException(404, f"Id {flight_id} not found. Range: 0–{len(_records)-1}.")
    return _records[flight_id]


@app.post("/flights", status_code=201, tags=["Flights"])
def create_flight(flight: FlightCreate):
    data = flight.model_dump(by_alias=True)
    data["num_stops"]       = {"zero":0,"one":1,"two_or_more":2}[data["stops"]]
    data["price_per_hour"]  = round(data["price"] / data["duration"], 2)
    data["is_early_booking"]= int(data["days_left"] > 30)
    _records.append(data)
    return {"message": "Flight added successfully.",
            "total_records": len(_records), "new_record": data}
