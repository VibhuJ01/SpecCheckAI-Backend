from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from src.enums import MongoCollectionsNames
from src.mongodb.masters.specification_matrix import SpecificationMatrixMaster
from src.utils import (
    employee_edit_permission,
    employee_page_permission,
    requires_verification,
)

router = APIRouter()
specification_matrix_db = SpecificationMatrixMaster()


@router.post("/add_specification")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.SPECIFICATION_MATRIX)
async def add_specification_matrix(request: Request, decoded_data: dict = {}):
    request_data = await request.json()

    response_data, status_code = specification_matrix_db.add_specification_matrix(
        request_data=request_data,
        current_user_email=decoded_data["email"],
        company_admin_email=decoded_data["company_admin_email"],
    )
    return JSONResponse(response_data, status_code=status_code)


@router.post("/update_specification")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.SPECIFICATION_MATRIX)
async def update_specification_matrix(request: Request, decoded_data: dict = {}):
    request_data = await request.json()

    response_data, status_code = specification_matrix_db.update_specification_matrix(
        request_data=request_data,
        current_user_email=decoded_data["email"],
        company_admin_email=decoded_data["company_admin_email"],
    )
    return JSONResponse(response_data, status_code=status_code)


@router.get("/fetch_all_specifications")
@requires_verification
@employee_page_permission(page_name=MongoCollectionsNames.SPECIFICATION_MATRIX)
async def fetch_all_specification_matrix(request: Request, decoded_data: dict = {}):
    response_data, status_code = specification_matrix_db.fetch_all_specification_matrix(
        company_admin_email=decoded_data["company_admin_email"]
    )
    return JSONResponse(response_data, status_code=status_code)


@router.delete("/delete_specification")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.SPECIFICATION_MATRIX)
async def delete_specification_matrix(request: Request, decoded_data: dict = {}, specification_code: str = Query(...)):
    response_data, status_code = specification_matrix_db.delete_specification_matrix(
        code=specification_code,
        current_user_email=decoded_data["email"],
        company_admin_email=decoded_data["company_admin_email"],
    )
    return JSONResponse(response_data, status_code=status_code)


@router.post("/add_standard")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.SPECIFICATION_MATRIX)
async def add_standard(request: Request, decoded_data: dict = {}):
    request_data = await request.json()

    response_data, status_code = specification_matrix_db.add_standard(
        current_user_email=decoded_data["email"],
        standard_data=request_data,
        company_admin_email=decoded_data["company_admin_email"],
    )
    return JSONResponse(response_data, status_code=status_code)


@router.post("/edit_standard")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.SPECIFICATION_MATRIX)
async def edit_standard(request: Request, decoded_data: dict = {}):
    request_data = await request.json()

    response_data, status_code = specification_matrix_db.edit_standard(
        current_user_email=decoded_data["email"],
        request_data=request_data,
        company_admin_email=decoded_data["company_admin_email"],
    )
    return JSONResponse(response_data, status_code=status_code)


@router.get("/fetch_standards_in_specification")
@requires_verification
@employee_page_permission(page_name=MongoCollectionsNames.SPECIFICATION_MATRIX)
async def fetch_standards_in_specification(
    request: Request, decoded_data: dict = {}, specification_code: str = Query(...)
):
    response_data, status_code = specification_matrix_db.fetch_standards_in_specification(
        specification_code=specification_code,
        company_admin_email=decoded_data["company_admin_email"],
    )
    return JSONResponse(response_data, status_code=status_code)


@router.delete("/delete_standard")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.SPECIFICATION_MATRIX)
async def delete_standard(request: Request, decoded_data: dict = {}, standard_code: str = Query(...)):
    response_data, status_code = specification_matrix_db.delete_standard(
        standard_code=standard_code,
        current_user_email=decoded_data["email"],
        company_admin_email=decoded_data["company_admin_email"],
    )
    return JSONResponse(response_data, status_code=status_code)
