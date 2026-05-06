from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # customer | workshop

    workshop_name = Column(String, nullable=True)
    address = Column(String, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class InventoryBattery(Base):
    __tablename__ = "inventory_batteries"

    id = Column(String, primary_key=True, index=True)
    workshop_user_id = Column(Integer, nullable=False, index=True)
    pack_id = Column(String, nullable=False, index=True)
    source = Column(String, nullable=True)
    chemistry = Column(String, nullable=True)
    ocv_v = Column(Float, nullable=True)
    capacity_ah = Column(Float, nullable=True)
    cycle_count = Column(Integer, nullable=True)
    temperature_c = Column(Float, nullable=True)
    age_days = Column(Integer, nullable=True)
    condition = Column(String, nullable=True)
    soh = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    recommended_action = Column(String, nullable=True)
    status = Column(String, nullable=False, default="active")
    pack_notes_json = Column(Text, nullable=True)
    pack_analysis_json = Column(Text, nullable=True)
    cell_analysis_json = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class MarketplaceListing(Base):
    __tablename__ = "marketplace_listings"

    id = Column(String, primary_key=True, index=True)
    inventory_battery_id = Column(String, nullable=False, unique=True, index=True)
    workshop_user_id = Column(Integer, nullable=False, index=True)
    model_name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    warranty_months = Column(Integer, nullable=False, default=6)
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
