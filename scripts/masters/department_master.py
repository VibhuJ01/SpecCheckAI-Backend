from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.enums import MongoCollectionsNames
from src.mongodb.masters.department_master import DepartmentMaster
from src.utils import (
    employee_edit_permission,
    employee_page_permission,
    requires_verification,
)

router = APIRouter()
department_master_db = DepartmentMaster()


@router.post("/add_department")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.DEPARTMENT_MASTER)
async def add_department(request: Request, decoded_data: dict = {}):
    request_data = await request.json()

    response_data, status_code = department_master_db.add_department(
        request_data=request_data,
        current_user_email=decoded_data["email"],
        company_admin_email=decoded_data["company_admin_email"],
    )
    return JSONResponse(response_data, status_code=status_code)


@router.post("/update_department")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.DEPARTMENT_MASTER)
async def update_department(request: Request, decoded_data: dict = {}):
    request_data = await request.json()

    response_data, status_code = department_master_db.edit_department(
        request_data=request_data,
        current_user_email=decoded_data["email"],
        company_admin_email=decoded_data["company_admin_email"],
    )
    return JSONResponse(response_data, status_code=status_code)


@router.get("/fetch_all_departments")
@requires_verification
@employee_page_permission(page_name=MongoCollectionsNames.DEPARTMENT_MASTER)
async def fetch_all_departments(request: Request, decoded_data: dict = {}):
    response_data, status_code = department_master_db.fetch_departments(
        company_admin_email=decoded_data["company_admin_email"]
    )
    return JSONResponse(response_data, status_code=status_code)
