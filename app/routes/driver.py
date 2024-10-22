# app/routes/driver.py
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from app.database import get_database
from app.schemas.driver import DriverCreate, DriverUpdate, DriverOut
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId, errors
from datetime import date, datetime
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

@router.post("/drivers/", response_model=DriverOut)
async def create_driver(driver: DriverCreate, db: AsyncIOMotorDatabase = Depends(get_database)):
    # Validate name
    if not driver.name or len(driver.name.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Invalid name",
                details="Driver name cannot be empty and must be at least 2 characters long",
                example="Example: 'John Doe'"
            )
        )

    # Check if license number is unique
    existing_driver = await db.drivers.find_one({"license_number": driver.license_number})
    if existing_driver:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="License number already registered",
                details=f"Driver with license number '{driver.license_number}' already exists",
                example="Please provide a unique license number"
            )
        )

    try:
        # Create driver document
        driver_dict = driver.dict()
        result = await db.drivers.insert_one(driver_dict)
        created_driver = await db.drivers.find_one({"_id": result.inserted_id})

        if not created_driver:
            raise HTTPException(
                status_code=500,
                detail=create_error_response(
                    message="Driver creation failed",
                    details="Failed to create driver record in database",
                    example="Please try again or contact support if the problem persists"
                )
            )

        return DriverOut(id=str(created_driver["_id"]), **{k: v for k, v in created_driver.items() if k != "_id"})

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                message="Internal server error",
                details=str(e),
                example="Please try again or contact support if the problem persists"
            )
        )

@router.get("/drivers/", response_model=List[DriverOut])
async def get_drivers(
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

        drivers = await db.drivers.find().skip(skip).limit(limit).to_list(length=limit)
        return [DriverOut(id=str(driver["_id"]), **{k: v for k, v in driver.items() if k != "_id"}) 
                for driver in drivers]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                message="Failed to retrieve drivers",
                details=str(e),
                example="Please try again or contact support if the problem persists"
            )
        )

@router.get("/drivers/{driver_id}", response_model=DriverOut)
async def get_driver(driver_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    try:
        driver_oid = ObjectId(driver_id)
    except errors.InvalidId:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Invalid driver ID format",
                details=f"The provided ID '{driver_id}' is not a valid MongoDB ObjectId",
                example="Expected format: '507f1f77bcf86cd799439011' (24 characters, hexadecimal)"
            )
        )

    driver = await db.drivers.find_one({"_id": driver_oid})
    if not driver:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                message="Driver not found",
                details=f"No driver found with ID: {driver_id}",
                example="Please ensure you're using a valid driver ID"
            )
        )

    return DriverOut(id=str(driver["_id"]), **{k: v for k, v in driver.items() if k != "_id"})

@router.put("/drivers/{driver_id}", response_model=DriverOut)
async def update_driver(driver_id: str, driver: DriverUpdate, db: AsyncIOMotorDatabase = Depends(get_database)):
    try:
        driver_oid = ObjectId(driver_id)
    except errors.InvalidId:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Invalid driver ID format",
                details=f"The provided ID '{driver_id}' is not a valid MongoDB ObjectId",
                example="Expected format: '507f1f77bcf86cd799439011' (24 characters, hexadecimal)"
            )
        )

    # Check if driver exists
    existing_driver = await db.drivers.find_one({"_id": driver_oid})
    if not existing_driver:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                message="Driver not found",
                details=f"No driver found with ID: {driver_id}",
                example="Please ensure you're using a valid driver ID"
            )
        )

    # Validate name
    if not driver.name or len(driver.name.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Invalid name",
                details="Driver name cannot be empty and must be at least 2 characters long",
                example="Example: 'John Doe'"
            )
        )

    # Check if new license number is unique (if it's being changed)
    if driver.license_number != existing_driver["license_number"]:
        duplicate_driver = await db.drivers.find_one({
            "_id": {"$ne": driver_oid},
            "license_number": driver.license_number
        })
        if duplicate_driver:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    message="License number already registered",
                    details=f"License number '{driver.license_number}' is already registered to another driver",
                    example="Please provide a unique license number"
                )
            )

    # Update the driver
    updated_driver = await db.drivers.find_one_and_update(
        {"_id": driver_oid},
        {"$set": driver.dict()},
        return_document=True
    )

    if not updated_driver:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                message="Update failed",
                details="Failed to update driver information",
                example="Please try again or contact support if the problem persists"
            )
        )

    return DriverOut(id=str(updated_driver["_id"]), **{k: v for k, v in updated_driver.items() if k != "_id"})

@router.delete("/drivers/{driver_id}")
async def delete_driver(driver_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    try:
        driver_oid = ObjectId(driver_id)
    except errors.InvalidId:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Invalid driver ID format",
                details=f"The provided ID '{driver_id}' is not a valid MongoDB ObjectId",
                example="Expected format: '507f1f77bcf86cd799439011' (24 characters, hexadecimal)"
            )
        )

    # Check if driver exists
    driver = await db.drivers.find_one({"_id": driver_oid})
    if not driver:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                message="Driver not found",
                details=f"No driver found with ID: {driver_id}",
                example="Please ensure you're using a valid driver ID"
            )
        )

    # Check if driver is assigned to any vehicle and has future allocations
    vehicle = await db.vehicles.find_one({"driver_id": driver_oid})
    if vehicle:
        # Check for future allocations
        today = datetime.combine(date.today(), datetime.min.time())
        future_allocation = await db.allocations.find_one({
            "vehicle_id": vehicle["_id"],
            "date": {"$gt": today}
        })
        
        if future_allocation:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    message="Cannot delete driver",
                    details=f"Driver's vehicle has future allocations scheduled",
                    example="Cancel all future allocations before deleting the driver"
                )
            )

        try:
            # Set driver_id to empty string instead of removing it
            result = await db.vehicles.update_one(
                {"_id": vehicle["_id"]},
                {"$set": {"driver_id": ""}}
            )
            
            if result.modified_count == 0:
                raise HTTPException(
                    status_code=500,
                    detail=create_error_response(
                        message="Failed to unassign driver",
                        details="Could not update vehicle's driver information",
                        example="Please try again or contact support if the problem persists"
                    )
                )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=create_error_response(
                    message="Vehicle update failed",
                    details=str(e),
                    example="Please try again or contact support if the problem persists"
                )
            )

    try:
        # Delete the driver
        delete_result = await db.drivers.delete_one({"_id": driver_oid})
        if delete_result.deleted_count == 0:
            raise HTTPException(
                status_code=500,
                detail=create_error_response(
                    message="Deletion failed",
                    details="Failed to delete the driver",
                    example="Please try again or contact support if the problem persists"
                )
            )

        return {
            "message": "Driver deleted successfully",
            "details": "Driver was unassigned from vehicle and deleted" if vehicle else "Driver was deleted"
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