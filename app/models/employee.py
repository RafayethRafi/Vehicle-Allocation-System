# app/models/employee.py
from pydantic import BaseModel, Field

class EmployeeModel(BaseModel):
    id: str = Field(default="", alias="_id")
    name: str
    department: str

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True