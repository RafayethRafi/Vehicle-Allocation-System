# app/schemas/allocation.py
from pydantic import BaseModel, Field, validator
from datetime import date
from .employee import EmployeeOut
from .vehicle import VehicleOut

class AllocationBase(BaseModel):
    employee_id: str = Field(..., description="Employee ID")
    vehicle_id: str = Field(..., description="Vehicle ID")
    date: date

class AllocationCreate(AllocationBase):
    pass

class AllocationUpdate(AllocationBase):
    pass

class AllocationOut(BaseModel):
    id: str
    employee: EmployeeOut
    vehicle: VehicleOut
    date: date

    class Config:
        from_attributes = True
        populate_by_name = True