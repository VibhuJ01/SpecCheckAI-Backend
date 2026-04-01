from typing import Optional

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse

from src.enums import MongoCollectionsNames
from src.mongodb.masters.employee_master import EmployeeMaster
from src.utils import (
    employee_edit_permission,
    employee_page_permission,
    requires_verification,
)

router = APIRouter()
employee_master_db = EmployeeMaster()


@router.post("/add_employee")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.EMPLOYEE_MASTER)
async def add_employee(request: Request, decoded_data: dict = {}):
    request_data = await request.json()
    response_data, status_code = employee_master_db.add_employee(
        request_data=request_data,
        current_user_email=decoded_data["email"],
        company_admin_email=decoded_data["company_admin_email"],
    )
    return JSONResponse(response_data, status_code=status_code)


@router.post("/update_employee")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.EMPLOYEE_MASTER)
async def update_employee(request: Request, decoded_data: dict = {}):
    request_data = await request.json()
    response_data, status_code = employee_master_db.update_employee(
        request_data=request_data,
        current_user_email=decoded_data["email"],
        company_admin_email=decoded_data["company_admin_email"],
    )
    return JSONResponse(response_data, status_code=status_code)


@router.get("/fetch_all_employees")
@requires_verification
@employee_page_permission(page_name=MongoCollectionsNames.EMPLOYEE_MASTER)
async def fetch_all_employees(request: Request, decoded_data: dict = {}):
    response_data, status_code = employee_master_db.fetch_all_employees(
        company_admin_email=decoded_data["company_admin_email"]
    )
    return JSONResponse(response_data, status_code=status_code)


@router.get("/enable_employee")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.EMPLOYEE_MASTER)
async def enable_employee(
    request: Request,
    employee_to_enable_email: str = Query("", description="Email of employee to enable"),
    decoded_data: dict = {},
):
    response_data, status_code = employee_master_db.enable_employee(
        enable_user_email=employee_to_enable_email, company_admin_email=decoded_data["company_admin_email"]
    )
    return JSONResponse(response_data, status_code=status_code)


@router.get("/disable_employee")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.EMPLOYEE_MASTER)
async def disable_employee(
    request: Request,
    employee_to_disable_email: str = Query("", description="Email of employee to disable"),
    decoded_data: dict = {},
):
    response_data, status_code = employee_master_db.disable_employee(
        disable_user_email=employee_to_disable_email,
        current_user_email=decoded_data["email"],
        company_admin_email=decoded_data["company_admin_email"],
    )
    return JSONResponse(response_data, status_code=status_code)


@router.get("/fetch_departments_dropdown")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.EMPLOYEE_MASTER)
async def fetch_departments_dropdown(request: Request, decoded_data: dict = {}):
    response_data, status_code = employee_master_db.fetch_departments_dropdown(
        company_admin_email=decoded_data["company_admin_email"]
    )
    return JSONResponse(response_data, status_code=status_code)


@router.get("/fetch_teams_dropdown")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.EMPLOYEE_MASTER)
async def fetch_teams_dropdown(request: Request, decoded_data: dict = {}):
    response_data, status_code = employee_master_db.fetch_teams_dropdown(
        company_admin_email=decoded_data["company_admin_email"]
    )
    return JSONResponse(response_data, status_code=status_code)


# ───────────────────── Employee Signature ─────────────────────


@router.post("/upsert_employee_signature")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.EMPLOYEE_MASTER)
async def upsert_employee_signature(
    request: Request,
    employee_email: str = Form(..., description="Email of the employee"),
    designation: str = Form(..., max_length=50, description="Employee designation (max 50 chars)"),
    dept_team_name: str = Form(..., max_length=50, description="Department or team name (max 50 chars)"),
    signature_file: Optional[UploadFile] = File(None, description="Signature image (JPG/PNG, max 500x500, 1 MB)"),
    decoded_data: dict = {},
):
    response_data, status_code = employee_master_db.upsert_employee_signature(
        employee_email=employee_email,
        designation=designation,
        dept_team_name=dept_team_name,
        current_user_email=decoded_data["email"],
        company_admin_email=decoded_data["company_admin_email"],
        signature_file=signature_file,
    )
    return JSONResponse(response_data, status_code=status_code)


@router.get("/fetch_employee_signature")
@requires_verification
@employee_page_permission(page_name=MongoCollectionsNames.EMPLOYEE_MASTER)
async def fetch_employee_signature(
    request: Request,
    employee_email: str = Query(..., description="Email of the employee"),
    decoded_data: dict = {},
):
    response_data, status_code = employee_master_db.fetch_employee_signature(
        employee_email=employee_email,
        company_admin_email=decoded_data["company_admin_email"],
    )
    return JSONResponse(response_data, status_code=status_code)


@router.delete("/delete_employee_signature")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.EMPLOYEE_MASTER)
async def delete_employee_signature(
    request: Request,
    employee_email: str = Query(..., description="Email of the employee"),
    decoded_data: dict = {},
):
    response_data, status_code = employee_master_db.delete_employee_signature(
        employee_email=employee_email,
        current_user_email=decoded_data["email"],
        company_admin_email=decoded_data["company_admin_email"],
    )
    return JSONResponse(response_data, status_code=status_code)
