from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from app.database import get_database
from app.schemas.vehicle import VehicleCreate, VehicleUpdate, VehicleOut
from app.schemas.driver import DriverOut
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId, errors
from datetime import date, datetime

router = APIRouter()

async def get_driver_data(db: AsyncIOMotorDatabase, driver_id: Optional[ObjectId]) -> DriverOut:
    """Helper function to get driver data with consistent empty handling"""
    if not driver_id:
        return DriverOut(id="", name="No Driver Assigned", license_number="N/A")
    
    try:
        driver = await db.drivers.find_one({"_id": driver_id})
        if driver:
            return DriverOut(id=str(driver["_id"]), **{k: v for k, v in driver.items() if k != "_id"})
    except Exception:
        pass
    
    return DriverOut(id="", name="No Driver Assigned", license_number="N/A")

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

@router.post("/vehicles/", response_model=VehicleOut)
async def create_vehicle(vehicle: VehicleCreate, db: AsyncIOMotorDatabase = Depends(get_database)):
    # Check if license plate is unique
    existing_vehicle = await db.vehicles.find_one({"license_plate": vehicle.license_plate})
    if existing_vehicle:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="License plate already registered",
                details=f"Vehicle with license plate '{vehicle.license_plate}' already exists",
                example="Each vehicle must have a unique license plate"
            )
        )

    # Handle driver assignment
    driver_oid = None
    if vehicle.driver_id:  # Changed from checking for empty string
        try:
            driver_oid = ObjectId(vehicle.driver_id)
            
            # Check if driver exists
            driver = await db.drivers.find_one({"_id": driver_oid})
            if not driver:
                raise HTTPException(
                    status_code=404,
                    detail=create_error_response(
                        message="Driver not found",
                        details=f"No driver found with ID: {vehicle.driver_id}",
                        example="Please provide a valid driver ID or leave empty for no driver"
                    )
                )

            # Check if driver is already assigned to any vehicle
            existing_allocation = await db.vehicles.find_one({"driver_id": driver_oid})
            if existing_allocation:
                raise HTTPException(
                    status_code=400,
                    detail=create_error_response(
                        message="Driver already assigned",
                        details=f"Driver is already assigned to vehicle with license plate: {existing_allocation['license_plate']}",
                        example="A driver can only be assigned to one vehicle at a time"
                    )
                )
            
        except errors.InvalidId:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    message="Invalid driver ID format",
                    details=f"The provided driver ID '{vehicle.driver_id}' is not valid",
                    example="Please provide a valid driver ID or leave empty for no driver"
                )
            )

    # Create vehicle document
    vehicle_dict = vehicle.dict()
    vehicle_dict["driver_id"] = str(driver_oid) if driver_oid else ""  # Store as string or empty string
    
    result = await db.vehicles.insert_one(vehicle_dict)
    created_vehicle = await db.vehicles.find_one({"_id": result.inserted_id})
    
    # Get driver data for response
    driver_out = await get_driver_data(db, ObjectId(vehicle_dict["driver_id"]) if vehicle_dict["driver_id"] else None)

    return VehicleOut(
        id=str(created_vehicle["_id"]),
        make=created_vehicle["make"],
        model=created_vehicle["model"],
        year=created_vehicle["year"],
        license_plate=created_vehicle["license_plate"],
        driver=driver_out
    )

@router.get("/vehicles/", response_model=List[VehicleOut])
async def get_vehicles(
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

        vehicles = await db.vehicles.find().skip(skip).limit(limit).to_list(length=limit)
        vehicle_outs = []
        
        for vehicle in vehicles:
            # Get driver data
            driver_out = await get_driver_data(db, vehicle.get("driver_id"))

            vehicle_outs.append(
                VehicleOut(
                    id=str(vehicle["_id"]),
                    make=vehicle["make"],
                    model=vehicle["model"],
                    year=vehicle["year"],
                    license_plate=vehicle["license_plate"],
                    driver=driver_out
                )
            )
        
        return vehicle_outs

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                message="Failed to retrieve vehicles",
                details=str(e),
                example="Please try again or contact support if the problem persists"
            )
        )

@router.get("/vehicles/{vehicle_id}", response_model=VehicleOut)
async def get_vehicle(vehicle_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    try:
        vehicle_oid = ObjectId(vehicle_id)
    except errors.InvalidId:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Invalid vehicle ID format",
                details=f"The provided ID '{vehicle_id}' is not valid",
                example="Expected format: '507f1f77bcf86cd799439011' (24 characters, hexadecimal)"
            )
        )

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

    # Get driver data
    driver_out = await get_driver_data(db, vehicle.get("driver_id"))

    return VehicleOut(
        id=str(vehicle["_id"]),
        make=vehicle["make"],
        model=vehicle["model"],
        year=vehicle["year"],
        license_plate=vehicle["license_plate"],
        driver=driver_out
    )

@router.put("/vehicles/{vehicle_id}", response_model=VehicleOut)
async def update_vehicle(vehicle_id: str, vehicle: VehicleUpdate, db: AsyncIOMotorDatabase = Depends(get_database)):
    try:
        vehicle_oid = ObjectId(vehicle_id)
    except errors.InvalidId:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Invalid vehicle ID format",
                details=f"The provided ID '{vehicle_id}' is not valid",
                example="Expected format: '507f1f77bcf86cd799439011' (24 characters, hexadecimal)"
            )
        )

    # Check if vehicle exists
    existing_vehicle = await db.vehicles.find_one({"_id": vehicle_oid})
    if not existing_vehicle:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                message="Vehicle not found",
                details=f"No vehicle found with ID: {vehicle_id}",
                example="Please ensure you're using a valid vehicle ID"
            )
        )

    # Check for future allocations
    today = datetime.combine(date.today(), datetime.min.time())
    future_allocation = await db.allocations.find_one({
        "vehicle_id": vehicle_oid,
        "date": {"$gt": today}
    })
    if future_allocation:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Vehicle has future allocations",
                details=f"Vehicle is allocated for future use (next allocation: {future_allocation['date'].date()})",
                example="Cancel all future allocations before modifying the vehicle"
            )
        )

    # Handle driver assignment
    driver_oid = None
    if vehicle.driver_id and vehicle.driver_id != "":
        try:
            driver_oid = ObjectId(vehicle.driver_id)
            driver = await db.drivers.find_one({"_id": driver_oid})
            if not driver:
                raise HTTPException(
                    status_code=404,
                    detail=create_error_response(
                        message="Driver not found",
                        details=f"No driver found with ID: {vehicle.driver_id}",
                        example="Please provide a valid driver ID or empty string for no driver"
                    )
                )

            # Check if driver is already assigned to any other vehicle
            existing_allocation = await db.vehicles.find_one({
                "driver_id": driver_oid,
                "_id": {"$ne": vehicle_oid}
            })
            if existing_allocation:
                raise HTTPException(
                    status_code=400,
                    detail=create_error_response(
                        message="Driver already assigned",
                        details=f"Driver is already assigned to vehicle with license plate: {existing_allocation['license_plate']}",
                        example="A driver can only be assigned to one vehicle at a time"
                    )
                )

        except errors.InvalidId:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    message="Invalid driver ID format",
                    details=f"The provided driver ID '{vehicle.driver_id}' is not valid",
                    example="Please provide a valid driver ID or empty string for no driver"
                )
            )

    # Check if new license plate is unique
    if vehicle.license_plate != existing_vehicle["license_plate"]:
        duplicate_vehicle = await db.vehicles.find_one({
            "_id": {"$ne": vehicle_oid},
            "license_plate": vehicle.license_plate
        })
        if duplicate_vehicle:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    message="License plate already registered",
                    details=f"License plate '{vehicle.license_plate}' is already assigned to another vehicle",
                    example="Each vehicle must have a unique license plate"
                )
            )

    # Update vehicle
    vehicle_dict = vehicle.dict()
    vehicle_dict["driver_id"] = driver_oid  # Store as ObjectId or None
    
    updated_vehicle = await db.vehicles.find_one_and_update(
        {"_id": vehicle_oid},
        {"$set": vehicle_dict},
        return_document=True
    )

    if not updated_vehicle:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                message="Update failed",
                details="Failed to update the vehicle information",
                example="Please try again or contact support if the problem persists"
            )
        )

    # Get driver data for response
    driver_out = await get_driver_data(db, updated_vehicle["driver_id"])

    return VehicleOut(
        id=str(updated_vehicle["_id"]),
        make=updated_vehicle["make"],
        model=updated_vehicle["model"],
        year=updated_vehicle["year"],
        license_plate=updated_vehicle["license_plate"],
        driver=driver_out
    )

@router.delete("/vehicles/{vehicle_id}")
async def delete_vehicle(vehicle_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    try:
        vehicle_oid = ObjectId(vehicle_id)
    except errors.InvalidId:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Invalid vehicle ID format",
                details=f"The provided ID '{vehicle_id}' is not a valid MongoDB ObjectId",
                example="Expected format: '507f1f77bcf86cd799439011' (24 characters, hexadecimal)"
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

    # Check for any future allocations
    today = datetime.combine(date.today(), datetime.min.time())
    future_allocation = await db.allocations.find_one({
        "vehicle_id": vehicle_oid,
        "date": {"$gt": today}
    })
    if future_allocation:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Cannot delete vehicle",
                details=f"Vehicle has future allocations (next allocation: {future_allocation['date'].date()})",
                example="Cancel all future allocations before deleting the vehicle"
            )
        )

    # Delete the vehicle
    delete_result = await db.vehicles.delete_one({"_id": vehicle_oid})
    if delete_result.deleted_count == 0:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                message="Deletion failed",
                details="Failed to delete the vehicle",
                example="Please try again or contact support if the problem persists"
            )
        )

    return {"message": "Vehicle deleted successfully"}




@router.get("/vehicles-unassigned/", response_model=List[VehicleOut])
async def get_unassigned_vehicles(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all vehicles that don't have assigned drivers"""
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

        # Query vehicles with empty driver_id
        vehicles = await db.vehicles.find(
            {"driver_id": ""}
        ).skip(skip).limit(limit).to_list(length=limit)
        
        vehicle_outs = []
        for vehicle in vehicles:
            # Get empty driver data
            driver_out = await get_driver_data(db, None)  # Will return default "No Driver Assigned" data

            vehicle_outs.append(
                VehicleOut(
                    id=str(vehicle["_id"]),
                    make=vehicle["make"],
                    model=vehicle["model"],
                    year=vehicle["year"],
                    license_plate=vehicle["license_plate"],
                    driver=driver_out
                )
            )
        
        return vehicle_outs

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                message="Failed to retrieve unassigned vehicles",
                details=str(e),
                example="Please try again or contact support if the problem persists"
            )
        )