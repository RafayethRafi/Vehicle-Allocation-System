# Vehicle Allocation System

A FastAPI-based system for managing company vehicles, drivers, and employee allocations. Built with FastAPI and MongoDB Atlas for efficient vehicle fleet management.

## Features

- Vehicle Management with driver assignment tracking
- Driver Management with license verification
- Employee Management by department
- Vehicle Allocation System with date-based scheduling
- Unassigned vehicles monitoring
- Comprehensive allocation reporting
- Built-in data validation and business rules

## Quick Start

1. **Clone the repository**:
   ```bash
   git clone git@github.com:RafayethRafi/Vehicle-Allocation-System.git
   cd Vehicle-Allocation-System
   ```

2. **Set up virtual environment**:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   Create a `.env` file:
   ```env
   MONGODB_URI="mongodb+srv://admin:PuEYEPoWAYGJxXTa@cluster0.r0ohl.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
   MONGODB_DB_NAME="vehicle_allocation"
   HOST="0.0.0.0"
   PORT=8000
   RELOAD=True
   API_PREFIX="/api"
   ```

5. **Run the application**:
   ```bash
   # Windows
   python -m app.main --reload

   # Linux/macOS
   python3 -m app.main --reload
   ```

6. **Access the API documentation**:
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`


## Project Structure

```
Vehicle-Allocation-System/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application instance and configuration
│   ├── config.py                # Environment and configuration settings
│   ├── database.py              # MongoDB connection and initialization
│   ├── models/
│   │   ├── __init__.py
│   │   ├── employee.py          # Employee model
│   │   ├── driver.py            # Driver model
│   │   ├── vehicle.py           # Vehicle model
│   │   └── allocation.py        # Allocation model
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── employee.py          # Employee endpoints
│   │   ├── driver.py            # Driver endpoints
│   │   ├── vehicle.py           # Vehicle endpoints
│   │   └── allocation.py        # Allocation endpoints
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── employee.py          # Employee Pydantic models
│   │   ├── driver.py            # Driver Pydantic models
│   │   ├── vehicle.py           # Vehicle Pydantic models
│   │   └── allocation.py        # Allocation Pydantic models
│   └── utils/
│       ├── __init__.py
│       └── object_id.py         # ObjectId utility functions
├── .env                         # Environment variables
├── .gitignore                  # Git ignore file
├── requirements.txt            # Project dependencies
└── README.md                  # Project documentation
```

### Key Components:

1. **Core Application Files:**
   - `main.py`: Application entry point and FastAPI setup
   - `config.py`: Environment variables and configuration
   - `database.py`: MongoDB connection handling

2. **Models Directory (`app/models/`):**
   - Database models for each entity
   - Defines data structure for MongoDB collections

3. **Routes Directory (`app/routes/`):**
   - API endpoint implementations
   - Business logic for each entity
   - Request handling and responses

4. **Schemas Directory (`app/schemas/`):**
   - Pydantic models for data validation
   - Request/Response schemas
   - API documentation models

5. **Utils Directory (`app/utils/`):**
   - Helper functions and utilities
   - ObjectId handling for MongoDB

6. **Configuration Files:**
   - `.env`: Environment configuration
   - `requirements.txt`: Python dependencies
   - `.gitignore`: Git ignore patterns



## API Documentation Explanation

### Vehicle Management

#### List Vehicles
```http
GET /api/vehicles
```
- Query Parameters:
  - `skip` (int, default: 0): Number of records to skip
  - `limit` (int, default: 100): Maximum number of records to return
- Returns: List of vehicles with their assigned drivers

#### Get Unassigned Vehicles
```http
GET /api/vehicles/unassigned
```
- Returns: List of vehicles that don't have assigned drivers

#### Create Vehicle
```http
POST /api/vehicles
```
- Body:
  ```json
  {
    "make": "string",
    "model": "string",
    "year": int,
    "license_plate": "string",
    "driver_id": "string" (optional)
  }
  ```
- Returns: Created vehicle details

#### Get Vehicle Details
```http
GET /api/vehicles/{vehicle_id}
```
- Returns: Detailed information about a specific vehicle

#### Update Vehicle
```http
PUT /api/vehicles/{vehicle_id}
```
- Body: Same as create vehicle
- Returns: Updated vehicle details

#### Delete Vehicle
```http
DELETE /api/vehicles/{vehicle_id}
```
- Returns: Success message

### Driver Management

#### List Drivers
```http
GET /api/drivers
```
- Query Parameters: skip, limit
- Returns: List of all drivers

#### Create Driver
```http
POST /api/drivers
```
- Body:
  ```json
  {
    "name": "string",
    "license_number": "string"
  }
  ```
- Returns: Created driver details

#### Update Driver
```http
PUT /api/drivers/{driver_id}
```
- Body: Same as create driver
- Returns: Updated driver details

### Employee Management

#### List Employees
```http
GET /api/employees
```
- Query Parameters: skip, limit
- Returns: List of all employees

#### Create Employee
```http
POST /api/employees
```
- Body:
  ```json
  {
    "name": "string",
    "department": "string"
  }
  ```
- Returns: Created employee details

### Allocation Management

#### List Allocations
```http
GET /api/allocations
```
- Query Parameters: skip, limit
- Returns: List of all vehicle allocations

#### Create Allocation
```http
POST /api/allocations
```
- Body:
  ```json
  {
    "employee_id": "string",
    "vehicle_id": "string",
    "date": "YYYY-MM-DD"
  }
  ```
- Returns: Created allocation details

#### Generate Allocation Report
```http
POST /api/allocations/report
```
- Body:
  ```json
  {
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "employee_id": "string" (optional),
    "vehicle_id": "string" (optional),
    "department": "string" (optional)
  }
  ```
- Returns: Detailed allocation report

## MongoDB Atlas Setup

1. Create MongoDB Atlas account at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a new cluster (free tier works)
3. Set up database access (create user with password)
4. Configure network access (add your IP or allow all IPs for development)
5. Get connection string and update .env file

## Deployment Overview

The application can be deployed on a VPS (Virtual Private Server) using:
- Nginx as reverse proxy
- Gunicorn as WSGI server
- Supervisor for process management
- SSL certificates for HTTPS

Key deployment steps:
1. Set up VPS with required dependencies
2. Configure Nginx and SSL
3. Set up application with production settings
4. Configure process management
5. Enable monitoring and logging

## Maintenance Overview

Regular maintenance includes:
1. Database maintenance:
   - Monitor performance
   - Regular backups
   - Index optimization

2. Application maintenance:
   - Log monitoring
   - Performance optimization
   - Regular updates
   - Security patches

3. Server maintenance:
   - System updates
   - SSL renewal
   - Resource monitoring

