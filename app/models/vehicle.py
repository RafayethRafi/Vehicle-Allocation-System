# app/models/vehicle.py
from pydantic import BaseModel, Field

class VehicleModel(BaseModel):
    id: str = Field(default="", alias="_id")
    make: str
    model: str
    year: int
    license_plate: str
    driver_id: str

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True