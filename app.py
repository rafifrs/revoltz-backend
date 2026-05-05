import json
from statistics import mean
from uuid import uuid4

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth_utils import decode_token
from database import Base, engine, get_db
from models import InventoryBattery, User
from routers.auth import router as auth_router

import os

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ReVoltz API", version="1.0.0")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

_bearer = HTTPBearer()


class PackScanPersistRequest(BaseModel):
    pack_data: dict
    pack_result: dict


class CellAnalysisPersistRequest(BaseModel):
    analysis_result: dict


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
    try:
        return decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def _current_user_id(current_user: dict) -> int:
    try:
        return int(current_user["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")


def _safe_json_loads(value: str | None):
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def serialize_inventory_battery(item: InventoryBattery) -> dict:
    pack_analysis = _safe_json_loads(item.pack_analysis_json) or {}
    cell_analysis = _safe_json_loads(item.cell_analysis_json)
    notes = _safe_json_loads(item.pack_notes_json) or []

    return {
      "id": item.id,
      "pack_id": item.pack_id,
      "source": item.source,
      "chemistry": item.chemistry,
      "ocv_v": item.ocv_v,
      "capacity_ah": item.capacity_ah,
      "cycle_count": item.cycle_count,
      "temperature_c": item.temperature_c,
      "age_days": item.age_days,
      "condition": item.condition,
      "soh": item.soh,
      "confidence_score": item.confidence_score,
      "recommended_action": item.recommended_action,
      "status": item.status,
      "last_updated": item.updated_at.strftime("%Y-%m-%d") if item.updated_at else None,
      "created_at": item.created_at.isoformat() if item.created_at else None,
      "updated_at": item.updated_at.isoformat() if item.updated_at else None,
      "pack_analysis": {
          **pack_analysis,
          "notes": notes,
      } if pack_analysis else {
          "pack_id": item.pack_id,
          "predicted_soh": item.soh,
          "confidence_score": item.confidence_score,
          "recommended_action": item.recommended_action,
          "notes": notes,
      },
      "cell_analysis": cell_analysis,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "revoltz-backend"}


@app.get("/model-health")
async def model_health():
    model_api_url = os.getenv("MODEL_API_URL", "http://localhost:8001")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{model_api_url}/health")
            return {"status": "ok", "model_api": resp.json()}
    except Exception as e:
        return {"status": "error", "model_api": str(e)}


@app.post("/inventory/pack-scan", status_code=status.HTTP_201_CREATED)
async def create_inventory_from_pack_scan(
    payload: PackScanPersistRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workshop_user_id = _current_user_id(current_user)
    pack_data = payload.pack_data
    pack_result = payload.pack_result

    battery_id = f"bat_{uuid4().hex[:8]}"
    pack_id = pack_result.get("pack_id") or pack_data.get("pack_id") or f"pack_{uuid4().hex[:8]}"

    item = InventoryBattery(
        id=battery_id,
        workshop_user_id=workshop_user_id,
        pack_id=pack_id,
        source=pack_data.get("source"),
        chemistry=pack_data.get("chemistry"),
        ocv_v=pack_data.get("ocv_v"),
        capacity_ah=pack_data.get("capacity_ah"),
        cycle_count=pack_data.get("cycle_count"),
        temperature_c=pack_data.get("temperature_c"),
        age_days=pack_data.get("age_days"),
        condition=pack_data.get("condition"),
        soh=pack_result.get("predicted_soh"),
        confidence_score=pack_result.get("confidence_score"),
        recommended_action=pack_result.get("recommended_action"),
        status="active",
        pack_notes_json=json.dumps(pack_result.get("notes", [])),
        pack_analysis_json=json.dumps(pack_result),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"battery": serialize_inventory_battery(item)}


@app.get("/inventory")
async def get_inventory(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workshop_user_id = _current_user_id(current_user)
    items = (
        db.query(InventoryBattery)
        .filter(InventoryBattery.workshop_user_id == workshop_user_id)
        .order_by(InventoryBattery.updated_at.desc(), InventoryBattery.created_at.desc())
        .all()
    )
    batteries = [serialize_inventory_battery(item) for item in items]
    return {"batteries": batteries, "total": len(batteries)}


@app.get("/inventory/{battery_id}")
async def get_inventory_battery_detail(
    battery_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workshop_user_id = _current_user_id(current_user)
    item = (
        db.query(InventoryBattery)
        .filter(
            InventoryBattery.id == battery_id,
            InventoryBattery.workshop_user_id == workshop_user_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Battery not found in inventory.")
    return {"battery": serialize_inventory_battery(item)}


@app.post("/inventory/{battery_id}/cell-analysis")
async def save_cell_analysis(
    battery_id: str,
    payload: CellAnalysisPersistRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workshop_user_id = _current_user_id(current_user)
    item = (
        db.query(InventoryBattery)
        .filter(
            InventoryBattery.id == battery_id,
            InventoryBattery.workshop_user_id == workshop_user_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Battery not found in inventory.")

    item.cell_analysis_json = json.dumps(payload.analysis_result)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"battery": serialize_inventory_battery(item)}


@app.get("/workshop/stats")
async def get_workshop_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workshop_user_id = _current_user_id(current_user)
    items = db.query(InventoryBattery).filter(InventoryBattery.workshop_user_id == workshop_user_id).all()

    total_batteries = len(items)
    soh_values = [item.soh for item in items if item.soh is not None]
    average_soh = mean(soh_values) if soh_values else 0

    sold_items = [item for item in items if item.status == "sold"]
    monthly_revenue = sum(((item.capacity_ah or 40) * 50000) for item in sold_items)
    co2_saved = round(sum(((item.capacity_ah or 40) * max(item.soh or 0, 0.25)) for item in items) * 0.01, 1)

    return {
        "total_batteries": total_batteries,
        "average_soh": average_soh,
        "monthly_revenue": monthly_revenue,
        "co2_saved": co2_saved,
    }


@app.get("/workshop/analytics/revenue")
async def get_revenue_analytics(current_user: dict = Depends(get_current_user)):
    return {
        "data": [
            {"date": "Jan 1", "amount": 500000},
            {"date": "Jan 5", "amount": 750000},
            {"date": "Jan 10", "amount": 600000},
            {"date": "Jan 15", "amount": 920000},
            {"date": "Jan 20", "amount": 1100000},
            {"date": "Jan 25", "amount": 1200000},
            {"date": "Jan 30", "amount": 1050000},
        ]
    }


@app.get("/workshop/analytics/soh-distribution")
async def get_soh_distribution(current_user: dict = Depends(get_current_user)):
    return {
        "data": [
            {"range": "0-40%", "count": 8},
            {"range": "40-60%", "count": 12},
            {"range": "60-80%", "count": 18},
            {"range": "80-100%", "count": 4},
        ]
    }


@app.get("/marketplace")
async def get_marketplace():
    return {
        "batteries": [
            {"id": "mkt_001", "model_name": "Tesla Model 3", "chemistry": "NMC", "soh": 0.85, "price": 39500000, "cycles": 290, "warranty_months": 12, "seller_location": "Jakarta", "seller_name": "Jakarta EV Workshop", "rating": 4.8, "verified": True, "age_days": 730, "capacity_ah": 75.0, "voltage_v": 350},
            {"id": "mkt_002", "model_name": "Nissan Leaf", "chemistry": "NMC", "soh": 0.80, "price": 28500000, "cycles": 450, "warranty_months": 6, "seller_location": "Surabaya", "seller_name": "Surabaya Battery Center", "rating": 4.8, "verified": True, "age_days": 1095, "capacity_ah": 40.0, "voltage_v": 360},
            {"id": "mkt_003", "model_name": "BYD Atto 3", "chemistry": "LFP", "soh": 0.88, "price": 52000000, "cycles": 310, "warranty_months": 12, "seller_location": "Bandung", "seller_name": "Bandung EV Solutions", "rating": 4.8, "verified": True, "age_days": 548, "capacity_ah": 60.0, "voltage_v": 320},
            {"id": "mkt_004", "model_name": "Hyundai Ioniq 5", "chemistry": "NMC", "soh": 0.84, "price": 58000000, "cycles": 385, "warranty_months": 18, "seller_location": "Jakarta", "seller_name": "Merdeka Battery", "rating": 4.7, "verified": True, "age_days": 640, "capacity_ah": 72.6, "voltage_v": 400},
            {"id": "mkt_005", "model_name": "Tesla Model Y", "chemistry": "NMC", "soh": 0.89, "price": 62000000, "cycles": 170, "warranty_months": 18, "seller_location": "Bali", "seller_name": "Bali Green Energy", "rating": 4.9, "verified": True, "age_days": 420, "capacity_ah": 75.0, "voltage_v": 350},
            {"id": "mkt_006", "model_name": "Nissan Leaf Gen2", "chemistry": "NMC", "soh": 0.76, "price": 22000000, "cycles": 620, "warranty_months": 3, "seller_location": "Surabaya", "seller_name": "Bali Green Energy", "rating": 4.6, "verified": True, "age_days": 1460, "capacity_ah": 40.0, "voltage_v": 360},
            {"id": "mkt_007", "model_name": "Wuling Air EV", "chemistry": "LFP", "soh": 0.67, "price": 18500000, "cycles": 295, "warranty_months": 6, "seller_location": "Yogyakarta", "seller_name": "Nusantara Battery", "rating": 4.5, "verified": False, "age_days": 820, "capacity_ah": 26.7, "voltage_v": 280},
            {"id": "mkt_008", "model_name": "BYD Dolphin", "chemistry": "LFP", "soh": 0.82, "price": 38000000, "cycles": 249, "warranty_months": 12, "seller_location": "Medan", "seller_name": "Tiga Roda EV", "rating": 4.7, "verified": True, "age_days": 600, "capacity_ah": 44.9, "voltage_v": 316},
            {"id": "mkt_009", "model_name": "Toyota bZ4X", "chemistry": "NMC", "soh": 0.91, "price": 68000000, "cycles": 100, "warranty_months": 24, "seller_location": "Jakarta", "seller_name": "Bandung EV Solutions", "rating": 4.9, "verified": True, "age_days": 280, "capacity_ah": 71.4, "voltage_v": 355},
        ]
    }
