import json
import sqlite3
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="E-Kurier L4H2 Smart Pricing & Logistics Agent", version="0.8.0")

def init_db():
    conn = sqlite3.connect("ekurier.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT,
            destination TEXT,
            weight TEXT,
            distance_km REAL,
            floor_price REAL,
            recommended_bid REAL,
            vehicle_match TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

@app.on_event("startup")
def startup_event():
    init_db()

class LoadItem(BaseModel):
    origin: str
    destination: str
    weight: str
    vehicle_match: str

class PricingRequest(BaseModel):
    origin: str
    destination: str
    one_way_distance_km: float
    diesel_price_per_litre: float
    return_scenario: str  # "ideal", "realistic", "worst"
    driver_days: float = 1.0

@app.get("/")
def read_root():
    return {"message": "E-Kurier Local Agent with Laravel Session & Smart Pricing is ready!"}

@app.get("/api/session/verify")
def verify_session():
    try:
        with open("session.json", "r") as f:
            session_data = json.load(f)
        cookies_count = len(session_data.get("cookies", []))
        return {"status": "success", "cookies_loaded": cookies_count, "message": "Session cookies are properly structured."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session file error: {str(e)}")

@app.post("/api/calculate-smart-bid")
def calculate_smart_bid(data: PricingRequest):
    try:
        multiplier = 2.0
        warning_msg = None

        if data.return_scenario == "ideal":
            multiplier = 1.15
        elif data.return_scenario == "realistic":
            multiplier = 1.3  # معامل ترجيحي 70% رجوع
        elif data.return_scenario == "worst":
            multiplier = 2.0
            warning_msg = "⚠️ تحذير خط الدفاع الأخير: عودة فارغة تامة، يجب تغطية التكلفة بالكامل!"

        total_distance = data.one_way_distance_km * multiplier
        fuel_cost = total_distance * 0.1 * data.diesel_price_per_litre
        maintenance_cost = total_distance * 0.12
        driver_wage_total = data.driver_days * 150.0

        # التكاليف الثابتة الشهرية (تأمين أليانز 30 + طريق 100 + تأمين سيارة 350 + قسط 1100 + برنامج 85 + ضريبة سنوية 17.5 + احتياطي ضريبة 200)
        monthly_fixed_total = 30 + 100 + 350 + 1100 + 85 + 17.5 + 200
        daily_fixed_allocation = monthly_fixed_total / 22.0
        trip_fixed_allocation = daily_fixed_allocation * data.driver_days

        floor_price = fuel_cost + maintenance_cost + driver_wage_total + trip_fixed_allocation

        aggressive_bid = floor_price * 1.10
        optimal_bid = floor_price * 1.25
        high_margin_bid = floor_price * 1.40

        return {
            "status": "success",
            "total_distance_km": round(total_distance, 2),
            "floor_price": round(floor_price, 2),
            "bids": {
                "aggressive_bid_هجومي": round(aggressive_bid, 2),
                "optimal_bid_التوازن": round(optimal_bid, 2),
                "high_margin_bid_الذروة": round(high_margin_bid, 2)
            },
            "warning_message": warning_msg
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))