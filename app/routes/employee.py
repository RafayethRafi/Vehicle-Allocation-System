# app/routes/employee.py
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from app.database import get_database
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeOut
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

@router.post("/employees/", response_model=EmployeeOut)
async def create_employee(employee: EmployeeCreate, db: AsyncIOMotorDatabase = Depends(get_database)):
    employee_dict = employee.dict()
    result = await db.employees.insert_one(employee_dict)
    created_employee = await db.employees.find_one({"_id": result.inserted_id})
    return EmployeeOut(id=str(created_employee["_id"]), **created_employee)

@router.get("/employees/", response_model=List[EmployeeOut])
async def get_employees(skip: int = 0, limit: int = 100, db: AsyncIOMotorDatabase = Depends(get_database)):
    employees = await db.employees.find().skip(skip).limit(limit).to_list(length=limit)
    return [EmployeeOut(id=str(employee["_id"]), **{k: v for k, v in employee.items() if k != "_id"}) for employee in employees]

@router.get("/employees/{employee_id}", response_model=EmployeeOut)
async def get_employee(employee_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    try:
        employee_oid = ObjectId(employee_id)
    except errors.InvalidId:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Invalid employee ID format",
                details=f"The provided ID '{employee_id}' is not a valid MongoDB ObjectId",
                example="Expected format: '507f1f77bcf86cd799439011' (24 characters, hexadecimal)"
            )
        )

    employee = await db.employees.find_one({"_id": employee_oid})
    if employee is None:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                message="Employee not found",
                details=f"No employee found with ID: {employee_id}",
                example="Please ensure you're using a valid employee ID"
            )
        )

    return EmployeeOut(id=str(employee["_id"]), **{k: v for k, v in employee.items() if k != "_id"})

@router.put("/employees/{employee_id}", response_model=EmployeeOut)
async def update_employee(employee_id: str, employee: EmployeeUpdate, db: AsyncIOMotorDatabase = Depends(get_database)):
    try:
        employee_oid = ObjectId(employee_id)
    except errors.InvalidId:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Invalid employee ID format",
                details=f"The provided ID '{employee_id}' is not a valid MongoDB ObjectId",
                example="Expected format: '507f1f77bcf86cd799439011' (24 characters, hexadecimal)"
            )
        )

    # Check if employee exists
    existing_employee = await db.employees.find_one({"_id": employee_oid})
    if not existing_employee:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                message="Employee not found",
                details=f"No employee found with ID: {employee_id}",
                example="Please ensure you're using a valid employee ID"
            )
        )

    # Check for future allocations before allowing department change
    # if employee.department != existing_employee["department"]:
    #     today = datetime.combine(date.today(), datetime.min.time())
    #     future_allocation = await db.allocations.find_one({
    #         "employee_id": employee_oid,
    #         "date": {"$gt": today}
    #     })
    #     if future_allocation:
    #         raise HTTPException(
    #             status_code=400,
    #             detail=create_error_response(
    #                 message="Cannot update department",
    #                 details="Employee has future vehicle allocations",
    #                 example="Cancel all future allocations before changing department"
    #             )
    #         )

    # Update the employee
    updated_employee = await db.employees.find_one_and_update(
        {"_id": employee_oid},
        {"$set": employee.dict()},
        return_document=True
    )

    if not updated_employee:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                message="Update failed",
                details="Failed to update employee information",
                example="Please try again or contact support if the problem persists"
            )
        )

    return EmployeeOut(id=str(updated_employee["_id"]), **{k: v for k, v in updated_employee.items() if k != "_id"})

@router.delete("/employees/{employee_id}")
async def delete_employee(employee_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    try:
        employee_oid = ObjectId(employee_id)
    except errors.InvalidId:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Invalid employee ID format",
                details=f"The provided ID '{employee_id}' is not a valid MongoDB ObjectId",
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

    # Check for any allocations (past or future)
    allocation = await db.allocations.find_one({"employee_id": employee_oid})
    if allocation:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Cannot delete employee",
                details="Employee has vehicle allocation history",
                example="Consider deleting the allocations before removing the employee"
            )
        )

    delete_result = await db.employees.delete_one({"_id": employee_oid})
    if delete_result.deleted_count == 0:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                message="Deletion failed",
                details="Failed to delete the employee",
                example="Please try again or contact support if the problem persists"
            )
        )

    return {"message": "Employee deleted successfully"}