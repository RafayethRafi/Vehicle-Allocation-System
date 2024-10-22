# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routes import employee_router, driver_router, vehicle_router, allocation_router, report_router
from app.database import connect_to_mongo, close_mongo_connection, init_db, insert_sample_data
from app.config import get_settings

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    await init_db()
    await insert_sample_data()
    yield
    # Shutdown
    await close_mongo_connection()

app = FastAPI(title="Vehicle Allocation System", lifespan=lifespan)

app.include_router(employee_router, prefix=settings.API_PREFIX, tags=["employees"])
app.include_router(driver_router, prefix=settings.API_PREFIX, tags=["drivers"])
app.include_router(vehicle_router, prefix=settings.API_PREFIX, tags=["vehicles"])
app.include_router(allocation_router, prefix=settings.API_PREFIX, tags=["allocations"])
app.include_router(report_router, prefix=settings.API_PREFIX, tags=["reports"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Vehicle Allocation System"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD
    )