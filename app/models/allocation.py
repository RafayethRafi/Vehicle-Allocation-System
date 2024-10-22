# app/models/allocation.py
from pydantic import BaseModel, Field
from datetime import date

class AllocationModel(BaseModel):
    id: str = Field(default="", alias="_id")
    employee_id: str
    vehicle_id: str
    date: date

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True