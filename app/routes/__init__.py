#app/routes/__init__.py

from .employee import router as employee_router
from .driver import router as driver_router
from .vehicle import router as vehicle_router
from .allocation import router as allocation_router
from .report import router as report_router