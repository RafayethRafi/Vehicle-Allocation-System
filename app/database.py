# app/database.py
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING
from bson import ObjectId
from datetime import date, datetime, timedelta
from app.config import get_settings

settings = get_settings()

class Database:
    client: AsyncIOMotorClient = None
    db = None

db = Database()

async def connect_to_mongo():
    db.client = AsyncIOMotorClient(settings.MONGODB_URI)
    db.db = db.client[settings.MONGODB_DB_NAME]
    print(f"Connected to MongoDB: {settings.MONGODB_DB_NAME}")

async def close_mongo_connection():
    if db.client:
        db.client.close()
        print("Closed MongoDB connection")

async def get_database():
    return db.db

async def init_db():
    if not db.client:
        await connect_to_mongo()
    try:
        # Create collections
        collections = await db.db.list_collection_names()
        if "employees" not in collections:
            await db.db.create_collection("employees")
        if "drivers" not in collections:
            await db.db.create_collection("drivers")
        if "vehicles" not in collections:
            await db.db.create_collection("vehicles")
        if "allocations" not in collections:
            await db.db.create_collection("allocations")

        # Create indexes for the specified fields
        
        # Employee indexes
        await db.db.employees.create_index([("department", ASCENDING)])
        
        # Vehicle indexes
        await db.db.vehicles.create_index([("driver_id", ASCENDING)])
        
        # Allocation indexes
        await db.db.allocations.create_index([("vehicle_id", ASCENDING)])
        await db.db.allocations.create_index([("employee_id", ASCENDING)])
        await db.db.allocations.create_index([("date", ASCENDING)])

        print("Database initialized successfully!")
        return True
    except Exception as e:
        print(f"Database initialization failed: {e}")
        return False

async def insert_sample_data():
    if not db.client:
        await connect_to_mongo()
    try:
        # Check if data already exists
        if await db.db.employees.count_documents({}) > 0:
            print("Sample data already exists. Skipping insertion.")
            return True

        # Sample employees
        employees = [
            {"name": "John Doe", "department": "Sales"},
            {"name": "Jane Smith", "department": "Marketing"},
            {"name": "Bob Johnson", "department": "IT"},
        ]
        employee_results = await db.db.employees.insert_many(employees)
        employee_ids = employee_results.inserted_ids

        # Sample drivers
        drivers = [
            {"name": "Alice Brown", "license_number": "DL12345"},
            {"name": "Charlie Davis", "license_number": "DL67890"},
            {"name": "Eva White", "license_number": "DL24680"},
        ]
        driver_results = await db.db.drivers.insert_many(drivers)
        driver_ids = driver_results.inserted_ids

        # Sample vehicles
        vehicles = [
            {"make": "Toyota", "model": "Camry", "year": 2022, "license_plate": "ABC123", "driver_id": driver_ids[0]},
            {"make": "Honda", "model": "Civic", "year": 2021, "license_plate": "XYZ789", "driver_id": driver_ids[1]},
            {"make": "Ford", "model": "F-150", "year": 2023, "license_plate": "DEF456", "driver_id": driver_ids[2]},
        ]
        vehicle_results = await db.db.vehicles.insert_many(vehicles)
        vehicle_ids = vehicle_results.inserted_ids

        # Sample allocations
        allocations = [
            {
                "employee_id": employee_ids[0],
                "vehicle_id": vehicle_ids[0],
                "date": datetime.combine(date.today() + timedelta(days=1), datetime.min.time())
            },
            {
                "employee_id": employee_ids[1],
                "vehicle_id": vehicle_ids[1],
                "date": datetime.combine(date.today() + timedelta(days=2), datetime.min.time())
            },
            {
                "employee_id": employee_ids[2],
                "vehicle_id": vehicle_ids[2],
                "date": datetime.combine(date.today() + timedelta(days=3), datetime.min.time())
            }
        ]
        await db.db.allocations.insert_many(allocations)

        print("Sample data inserted successfully!")
        return True
    except Exception as e:
        print(f"Failed to insert sample data: {e}")
        return False