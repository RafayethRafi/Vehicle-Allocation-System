from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from app.database import get_database
from datetime import date, datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId, errors
from pydantic import BaseModel

router = APIRouter()

class AllocationReportFilter(BaseModel):
    """Filter criteria for allocation report"""
    # Date filters
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    # Entity filters
    employee_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    driver_id: Optional[str] = None
    department: Optional[str] = None

class AllocationReportEntry(BaseModel):
    """Individual allocation entry in the report"""
    allocation_id: str
    date: date
    employee: Dict[str, str]  # {id, name, department}
    vehicle: Dict[str, Any]   # {id, make, model, year, license_plate}
    driver: Dict[str, str]    # {id, name, license_number}

class AllocationReport(BaseModel):
    """Complete allocation report response"""
    total_records: int
    allocations: List[AllocationReportEntry]

async def build_mongo_query(filters: AllocationReportFilter, db: AsyncIOMotorDatabase) -> Dict:
    """Build MongoDB query from filter criteria"""
    query = {}
    
    # Date range filter
    if filters.start_date or filters.end_date:
        query["date"] = {}
        if filters.start_date:
            query["date"]["$gte"] = datetime.combine(filters.start_date, datetime.min.time())
        if filters.end_date:
            query["date"]["$lte"] = datetime.combine(filters.end_date, datetime.max.time())

    # Employee filter
    if filters.employee_id:
        try:
            query["employee_id"] = ObjectId(filters.employee_id)
        except errors.InvalidId:
            raise HTTPException(status_code=400, detail="Invalid employee ID format")

    # Vehicle filter
    if filters.vehicle_id:
        try:
            query["vehicle_id"] = ObjectId(filters.vehicle_id)
        except errors.InvalidId:
            raise HTTPException(status_code=400, detail="Invalid vehicle ID format")

    # Driver filter - need to first find vehicles with this driver
    if filters.driver_id:
        try:
            driver_oid = ObjectId(filters.driver_id)
            vehicles = await db.vehicles.find({"driver_id": driver_oid}, {"_id": 1}).to_list(length=None)
            vehicle_ids = [vehicle["_id"] for vehicle in vehicles]
            if vehicle_ids:
                query["vehicle_id"] = {"$in": vehicle_ids}
            else:
                # If no vehicles found for driver, return no results
                query["vehicle_id"] = None
        except errors.InvalidId:
            raise HTTPException(status_code=400, detail="Invalid driver ID format")

    # Department filter - need to first find employees in this department
    if filters.department:
        employees = await db.employees.find(
            {"department": filters.department}, 
            {"_id": 1}
        ).to_list(length=None)
        employee_ids = [emp["_id"] for emp in employees]
        if employee_ids:
            query["employee_id"] = {"$in": employee_ids}
        else:
            # If no employees found in department, return no results
            query["employee_id"] = None

    return query

@router.post("/allocations/report", response_model=AllocationReport)
async def generate_allocation_report(
    filters: AllocationReportFilter,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        # Build query from filters
        query = await build_mongo_query(filters, db)
        
        # Get total count
        total_records = await db.allocations.count_documents(query)
        
        # Get allocations
        allocations = await db.allocations.find(query).sort("date", -1).to_list(length=None)
        
        # Process allocations
        processed_allocations = []
        for allocation in allocations:
            # Get employee data
            employee = await db.employees.find_one({"_id": allocation["employee_id"]})
            if not employee:
                continue
                
            # Get vehicle data
            vehicle = await db.vehicles.find_one({"_id": allocation["vehicle_id"]})
            if not vehicle:
                continue
                
            # Get driver data
            driver = None
            if vehicle.get("driver_id"):
                driver = await db.drivers.find_one({"_id": vehicle["driver_id"]})
            
            if not driver:
                driver = {"_id": "", "name": "No Driver Assigned", "license_number": "N/A"}
            
            processed_allocations.append(
                AllocationReportEntry(
                    allocation_id=str(allocation["_id"]),
                    date=allocation["date"].date(),
                    employee={
                        "id": str(employee["_id"]),
                        "name": employee["name"],
                        "department": employee["department"]
                    },
                    vehicle={
                        "id": str(vehicle["_id"]),
                        "make": vehicle["make"],
                        "model": vehicle["model"],
                        "year": vehicle["year"],
                        "license_plate": vehicle["license_plate"]
                    },
                    driver={
                        "id": str(driver["_id"]),
                        "name": driver["name"],
                        "license_number": driver["license_number"]
                    }
                )
            )
        
        return AllocationReport(
            total_records=total_records,
            allocations=processed_allocations
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to generate allocation report",
                "details": str(e)
            }
        )