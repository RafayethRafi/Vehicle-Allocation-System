# app/routes/allocation.py
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from app.database import get_database
from app.schemas.allocation import AllocationCreate, AllocationUpdate, AllocationOut
from app.schemas.employee import EmployeeOut
from app.schemas.vehicle import VehicleOut
from app.schemas.driver import DriverOut
from datetime import date, datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId, errors

router = APIRouter()

def create_error_response(
    message: str, 
    details: Optional[str] = None, 
    example: Optional[str] = None
) -> Dict[str, Any]:
    """Create a detailed error response"""
    response = {
        "message": message,
        "details": details if details else message
    }
    if example:
        response["example"] = example
    return response

async def validate_entities(db: AsyncIOMotorDatabase, employee_id: str, vehicle_id: str):
    """Validate employee and vehicle existence and availability."""
    try:
        employee_oid = ObjectId(employee_id)
        vehicle_oid = ObjectId(vehicle_id)
    except errors.InvalidId:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Invalid ID format",
                details=f"One or more provided IDs are not valid MongoDB ObjectIds",
                example="Expected format: '507f1f77bcf86cd799439011' (24 characters, hexadecimal)"
            )
        )

    # Check if employee exists
    employee = await db.employees.find_one({"_id": employee_oid})
    if not employee:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                message="Employee not found",
                details=f"No employee found with ID: {employee_id}",
                example="Please ensure you're using a valid employee ID"
            )
        )

    # Check if vehicle exists
    vehicle = await db.vehicles.find_one({"_id": vehicle_oid})
    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                message="Vehicle not found",
                details=f"No vehicle found with ID: {vehicle_id}",
                example="Please ensure you're using a valid vehicle ID"
            )
        )

    # Check if vehicle has an assigned driver
    if not vehicle.get("driver_id"):
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Vehicle unavailable",
                details="Vehicle has no assigned driver",
                example="Only vehicles with assigned drivers can be allocated"
            )
        )

    try:
        driver = await db.drivers.find_one({"_id": vehicle["driver_id"]})
        if not driver:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    message="Vehicle unavailable",
                    details="Associated driver not found",
                    example="Please ensure the vehicle has a valid driver assignment"
                )
            )
    except errors.InvalidId:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                message="Invalid driver reference",
                details="Vehicle contains invalid driver reference",
                example="Please contact support to resolve this issue"
            )
        )

    return employee, vehicle, driver

async def check_vehicle_availability(
    db: AsyncIOMotorDatabase,
    vehicle_id: ObjectId,
    check_date: datetime,
    exclude_allocation_id: Optional[ObjectId] = None
) -> None:
    """Check if vehicle is available on the specified date."""
    query = {
        "vehicle_id": vehicle_id,
        "date": check_date
    }
    
    if exclude_allocation_id:
        query["_id"] = {"$ne": exclude_allocation_id}
    
    existing_allocation = await db.allocations.find_one(query)
    if existing_allocation:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Vehicle not available",
                details=f"Vehicle is already allocated for {check_date.date()}",
                example="Please select a different date or vehicle"
            )
        )

async def check_employee_allocation(
    db: AsyncIOMotorDatabase,
    employee_id: ObjectId,
    check_date: datetime,
    exclude_allocation_id: Optional[ObjectId] = None
) -> None:
    """Check if employee already has a vehicle allocated on the specified date."""
    query = {
        "employee_id": employee_id,
        "date": check_date
    }
    
    if exclude_allocation_id:
        query["_id"] = {"$ne": exclude_allocation_id}
    
    existing_allocation = await db.allocations.find_one(query)
    if existing_allocation:
        vehicle = await db.vehicles.find_one({"_id": existing_allocation["vehicle_id"]})
        license_plate = vehicle["license_plate"] if vehicle else "Unknown"
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Employee already has an allocation",
                details=f"Employee already has vehicle {license_plate} allocated for {check_date.date()}",
                example="An employee can only be allocated one vehicle per day"
            )
        )

@router.post("/allocations/", response_model=AllocationOut)
async def create_allocation(allocation: AllocationCreate, db: AsyncIOMotorDatabase = Depends(get_database)):
    # Validate date
    if allocation.date < date.today():
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Invalid allocation date",
                details="Allocation date must be in the future",
                example=f"Current date: {date.today()}, Please select a future date"
            )
        )

    # Validate entities
    employee, vehicle, driver = await validate_entities(db, allocation.employee_id, allocation.vehicle_id)

    # Convert date to datetime and check availability
    allocation_date = datetime.combine(allocation.date, datetime.min.time())
    
    # Check vehicle availability
    await check_vehicle_availability(db, ObjectId(allocation.vehicle_id), allocation_date)
    
    # Check if employee already has a vehicle allocated for this date
    await check_employee_allocation(db, ObjectId(allocation.employee_id), allocation_date)

    try:
        # Create allocation document
        allocation_dict = {
            "employee_id": ObjectId(allocation.employee_id),
            "vehicle_id": ObjectId(allocation.vehicle_id),
            "date": allocation_date
        }
        
        result = await db.allocations.insert_one(allocation_dict)
        created_allocation = await db.allocations.find_one({"_id": result.inserted_id})
        
        if not created_allocation:
            raise HTTPException(
                status_code=500,
                detail=create_error_response(
                    message="Allocation creation failed",
                    details="Failed to create allocation record",
                    example="Please try again or contact support"
                )
            )

        return AllocationOut(
            id=str(created_allocation["_id"]),
            employee=EmployeeOut(id=str(employee["_id"]), **{k: v for k, v in employee.items() if k != "_id"}),
            vehicle=VehicleOut(
                id=str(vehicle["_id"]),
                make=vehicle["make"],
                model=vehicle["model"],
                year=vehicle["year"],
                license_plate=vehicle["license_plate"],
                driver=DriverOut(id=str(driver["_id"]), **{k: v for k, v in driver.items() if k != "_id"})
            ),
            date=created_allocation["date"].date()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                message="Internal server error",
                details=str(e),
                example="Please try again or contact support"
            )
        )

@router.get("/allocations/", response_model=List[AllocationOut])
async def get_allocations(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        if skip < 0:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    message="Invalid skip value",
                    details="Skip value cannot be negative",
                    example="Use skip=0 for first page"
                )
            )
        
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    message="Invalid limit value",
                    details="Limit must be between 1 and 100",
                    example="Use limit=10 for 10 items per page"
                )
            )

        allocations = await db.allocations.find().skip(skip).limit(limit).to_list(length=limit)
        allocation_outs = []
        
        for allocation in allocations:
            try:
                employee = await db.employees.find_one({"_id": allocation["employee_id"]})
                vehicle = await db.vehicles.find_one({"_id": allocation["vehicle_id"]})
                
                if not employee or not vehicle:
                    continue
                
                driver = None
                if vehicle.get("driver_id"):
                    try:
                        driver = await db.drivers.find_one({"_id": ObjectId(vehicle["driver_id"])})
                    except errors.InvalidId:
                        pass

                if not driver:
                    driver = {"_id": "", "name": "No Driver Assigned", "license_number": "N/A"}

                allocation_outs.append(
                    AllocationOut(
                        id=str(allocation["_id"]),
                        employee=EmployeeOut(
                            id=str(employee["_id"]),
                            **{k: v for k, v in employee.items() if k != "_id"}
                        ),
                        vehicle=VehicleOut(
                            id=str(vehicle["_id"]),
                            make=vehicle["make"],
                            model=vehicle["model"],
                            year=vehicle["year"],
                            license_plate=vehicle["license_plate"],
                            driver=DriverOut(
                                id=str(driver["_id"]),
                                **{k: v for k, v in driver.items() if k != "_id"}
                            )
                        ),
                        date=allocation["date"].date() if isinstance(allocation["date"], datetime) else allocation["date"]
                    )
                )
            except Exception:
                # Skip any allocation with invalid data
                continue
        
        return allocation_outs

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                message="Failed to retrieve allocations",
                details=str(e),
                example="Please try again or contact support"
            )
        )

@router.get("/allocations/{allocation_id}", response_model=AllocationOut)
async def get_allocation(allocation_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    try:
        allocation_oid = ObjectId(allocation_id)
    except errors.InvalidId:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Invalid allocation ID format",
                details=f"The provided ID '{allocation_id}' is not a valid MongoDB ObjectId",
                example="Expected format: '507f1f77bcf86cd799439011' (24 characters, hexadecimal)"
            )
        )

    allocation = await db.allocations.find_one({"_id": allocation_oid})
    if not allocation:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                message="Allocation not found",
                details=f"No allocation found with ID: {allocation_id}",
                example="Please ensure you're using a valid allocation ID"
            )
        )

    try:
        # Get related entities
        employee = await db.employees.find_one({"_id": allocation["employee_id"]})
        if not employee:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    message="Referenced employee not found",
                    details="The employee associated with this allocation no longer exists",
                    example="This may indicate a data consistency issue"
                )
            )

        vehicle = await db.vehicles.find_one({"_id": allocation["vehicle_id"]})
        if not vehicle:
            raise HTTPException(
                status_code=404,
                detail=create_error_response(
                    message="Referenced vehicle not found",
                    details="The vehicle associated with this allocation no longer exists",
                    example="This may indicate a data consistency issue"
                )
            )

        driver = None
        if vehicle.get("driver_id"):
            try:
                driver = await db.drivers.find_one({"_id": ObjectId(vehicle["driver_id"])})
            except errors.InvalidId:
                pass

        if not driver:
            driver = {"_id": "", "name": "No Driver Assigned", "license_number": "N/A"}

        return AllocationOut(
            id=str(allocation["_id"]),
            employee=EmployeeOut(
                id=str(employee["_id"]),
                **{k: v for k, v in employee.items() if k != "_id"}
            ),
            vehicle=VehicleOut(
                id=str(vehicle["_id"]),
                make=vehicle["make"],
                model=vehicle["model"],
                year=vehicle["year"],
                license_plate=vehicle["license_plate"],
                driver=DriverOut(
                    id=str(driver["_id"]),
                    **{k: v for k, v in driver.items() if k != "_id"}
                )
            ),
            date=allocation["date"].date() if isinstance(allocation["date"], datetime) else allocation["date"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                message="Failed to retrieve allocation details",
                details=str(e),
                example="Please try again or contact support"
            )
        )

@router.put("/allocations/{allocation_id}", response_model=AllocationOut)
async def update_allocation(
    allocation_id: str, 
    allocation: AllocationUpdate, 
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        allocation_oid = ObjectId(allocation_id)
    except errors.InvalidId:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Invalid allocation ID format",
                details=f"The provided ID '{allocation_id}' is not a valid MongoDB ObjectId",
                example="Expected format: '507f1f77bcf86cd799439011' (24 characters, hexadecimal)"
            )
        )

    # Check if the allocation exists
    existing_allocation = await db.allocations.find_one({"_id": allocation_oid})
    if not existing_allocation:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                message="Allocation not found",
                details=f"No allocation found with ID: {allocation_id}",
                example="Please ensure you're using a valid allocation ID"
            )
        )

    # Validate allocation date
    if allocation.date < date.today():
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Invalid allocation date",
                details="Allocation date must be in the future",
                example=f"Current date: {date.today()}, Please select a future date"
            )
        )

    # Check if the existing allocation is in the past
    existing_date = existing_allocation["date"].date() if isinstance(existing_allocation["date"], datetime) else existing_allocation["date"]
    if existing_date < date.today():
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Cannot modify past allocation",
                details=f"Allocation date {existing_date} has already passed",
                example="Only future allocations can be modified"
            )
        )

    # Validate entities and check availability
    employee, vehicle, driver = await validate_entities(db, allocation.employee_id, allocation.vehicle_id)
    allocation_date = datetime.combine(allocation.date, datetime.min.time())
    
    # Check vehicle availability (excluding current allocation)
    await check_vehicle_availability(db, ObjectId(allocation.vehicle_id), allocation_date, allocation_oid)
    
    # Check employee allocation (excluding current allocation)
    await check_employee_allocation(db, ObjectId(allocation.employee_id), allocation_date, allocation_oid)

    try:
        # Update allocation document
        allocation_dict = {
            "employee_id": ObjectId(allocation.employee_id),
            "vehicle_id": ObjectId(allocation.vehicle_id),
            "date": allocation_date
        }
        
        updated_allocation = await db.allocations.find_one_and_update(
            {"_id": allocation_oid},
            {"$set": allocation_dict},
            return_document=True
        )
        
        if not updated_allocation:
            raise HTTPException(
                status_code=500,
                detail=create_error_response(
                    message="Update failed",
                    details="Failed to update the allocation",
                    example="Please try again or contact support if the problem persists"
                )
            )

        return AllocationOut(
            id=str(updated_allocation["_id"]),
            employee=EmployeeOut(
                id=str(employee["_id"]),
                **{k: v for k, v in employee.items() if k != "_id"}
            ),
            vehicle=VehicleOut(
                id=str(vehicle["_id"]),
                make=vehicle["make"],
                model=vehicle["model"],
                year=vehicle["year"],
                license_plate=vehicle["license_plate"],
                driver=DriverOut(
                    id=str(driver["_id"]),
                    **{k: v for k, v in driver.items() if k != "_id"}
                )
            ),
            date=updated_allocation["date"].date()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                message="Update failed",
                details=str(e),
                example="Please try again or contact support if the problem persists"
            )
        )

@router.delete("/allocations/{allocation_id}")
async def delete_allocation(allocation_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    try:
        allocation_oid = ObjectId(allocation_id)
    except errors.InvalidId:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Invalid allocation ID format",
                details=f"The provided ID '{allocation_id}' is not a valid MongoDB ObjectId",
                example="Expected format: '507f1f77bcf86cd799439011' (24 characters, hexadecimal)"
            )
        )

    # Check if the allocation exists
    existing_allocation = await db.allocations.find_one({"_id": allocation_oid})
    if not existing_allocation:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                message="Allocation not found",
                details=f"No allocation found with ID: {allocation_id}",
                example="Please ensure you're using a valid allocation ID"
            )
        )

    # Check if the allocation is in the past
    allocation_date = existing_allocation["date"].date() if isinstance(existing_allocation["date"], datetime) else existing_allocation["date"]
    if allocation_date < date.today():
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Cannot delete past allocation",
                details=f"Allocation date {allocation_date} has already passed",
                example="Only future allocations can be deleted"
            )
        )

    try:
        # Delete the allocation
        delete_result = await db.allocations.delete_one({"_id": allocation_oid})
        
        if delete_result.deleted_count == 0:
            raise HTTPException(
                status_code=500,
                detail=create_error_response(
                    message="Deletion failed",
                    details="Failed to delete the allocation",
                    example="Please try again or contact support if the problem persists"
                )
            )

        return {
            "message": "Allocation deleted successfully",
            "details": {
                "id": allocation_id,
                "date": str(allocation_date)
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                message="Deletion failed",
                details=str(e),
                example="Please try again or contact support if the problem persists"
            )
        )
