# app/schemas/vehicle.py
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from .driver import DriverOut

class VehicleBase(BaseModel):
    make: str
    model: str
    year: int
    license_plate: str

class VehicleCreate(VehicleBase):
    driver_id: Optional[str] = Field(None, description="Driver ID as a string, can be None")

class VehicleUpdate(VehicleBase):
    driver_id: Optional[str] = Field(None, description="Driver ID as a string, can be None")

class VehicleOut(VehicleBase):
    id: str
    driver: DriverOut

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)