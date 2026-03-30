from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, Response

from src.enums import MongoCollectionsNames
from src.mongodb.masters.client_master import ClientMaster
from src.utils import (
    employee_edit_permission,
    employee_page_permission,
    requires_verification,
)

router = APIRouter()
client_master_db = ClientMaster()


@router.post("/add_client")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.CLIENT_MASTER)
async def add_client(request: Request, decoded_data: dict = {}):
    request_data = await request.json()

    response_data, status_code = client_master_db.add_client(
        request_data=request_data,
        current_user_email=decoded_data["email"],
        company_admin_email=decoded_data["email"],
    )
    return JSONResponse(response_data, status_code=status_code)


@router.post("/update_client")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.CLIENT_MASTER)
async def update_client(request: Request, decoded_data: dict = {}):
    request_data = await request.json()

    response_data, status_code = client_master_db.update_client(
        request_data=request_data,
        current_user_email=decoded_data["email"],
        company_admin_email=decoded_data["email"],
    )
    return JSONResponse(response_data, status_code=status_code)


@router.get("/fetch_all_clients")
@requires_verification
@employee_page_permission(page_name=MongoCollectionsNames.CLIENT_MASTER)
async def fetch_all_clients(request: Request, decoded_data: dict = {}):
    response_data, status_code = client_master_db.fetch_all_clients(company_admin_email=decoded_data["email"])
    return JSONResponse(response_data, status_code=status_code)


@router.delete("/delete_client")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.CLIENT_MASTER)
async def delete_client(
    request: Request,
    decoded_data: dict = {},
    client_code: str = Query(..., description="Unique code of the client to be deleted"),
):

    response_data, status_code = client_master_db.delete_client(
        client_code=client_code.strip(),
        current_user_email=decoded_data["email"],
        company_admin_email=decoded_data["email"],
    )
    return JSONResponse(response_data, status_code=status_code)


@router.get("/download_clients_csv")
@requires_verification
@employee_page_permission(page_name=MongoCollectionsNames.CLIENT_MASTER)
async def download_clients_csv(request: Request, decoded_data: dict = {}):

    response_data, status_code = client_master_db.download_client_as_csv(company_admin_email=decoded_data["email"])

    if status_code != 200:
        return JSONResponse(response_data, status_code=status_code)

    return Response(
        content=response_data["csv_data"],
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="clients.csv"'},
        status_code=status_code,
    )
