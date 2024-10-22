# app/schemas/driver.py
from pydantic import BaseModel, Field

class DriverBase(BaseModel):
    name: str
    license_number: str

class DriverCreate(DriverBase):
    pass

class DriverUpdate(DriverBase):
    pass

class DriverOut(DriverBase):
    id: str

    class Config:
        from_attributes = True
        populate_by_name = True