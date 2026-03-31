from fastapi import APIRouter, Request
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
