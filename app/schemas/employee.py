# app/schemas/employee.py
from pydantic import BaseModel, Field

class EmployeeBase(BaseModel):
    name: str
    department: str

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(EmployeeBase):
    pass

class EmployeeOut(EmployeeBase):
    id: str

    class Config:
        from_attributes = True
        populate_by_name = True