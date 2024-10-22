# app/models/driver.py
from pydantic import BaseModel, Field

class DriverModel(BaseModel):
    id: str = Field(default="", alias="_id")
    name: str
    license_number: str

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True