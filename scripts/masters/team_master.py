from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from src.enums import MongoCollectionsNames
from src.mongodb.masters.team_master import TeamMaster
from src.utils import (
    employee_edit_permission,
    employee_page_permission,
    requires_verification,
)

router = APIRouter()
team_master_db = TeamMaster()


@router.post("/add_team")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.TEAM_MASTER)
async def add_team(request: Request, decoded_data: dict = {}):
    request_data = await request.json()

    response_data, status_code = team_master_db.add_team(
        request_data=request_data,
        current_user_email=decoded_data["email"],
        company_admin_email=decoded_data["company_admin_email"],
    )
    return JSONResponse(response_data, status_code=status_code)


@router.post("/update_team")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.TEAM_MASTER)
async def update_team(request: Request, decoded_data: dict = {}):
    request_data = await request.json()

    response_data, status_code = team_master_db.update_team(
        request_data=request_data,
        current_user_email=decoded_data["email"],
        company_admin_email=decoded_data["company_admin_email"],
    )
    return JSONResponse(response_data, status_code=status_code)


@router.get("/fetch_all_teams")
@requires_verification
@employee_page_permission(page_name=MongoCollectionsNames.TEAM_MASTER)
async def fetch_all_teams(request: Request, decoded_data: dict = {}):
    response_data, status_code = team_master_db.fetch_all_teams(company_admin_email=decoded_data["company_admin_email"])
    return JSONResponse(response_data, status_code=status_code)


@router.delete("/delete_team")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.TEAM_MASTER)
async def delete_team(
    request: Request,
    decoded_data: dict = {},
    team_code: str = Query(..., description="Unique code of the team to be deleted"),
):

    response_data, status_code = team_master_db.delete_team(
        team_code=team_code.strip(),
        current_user_email=decoded_data["email"],
        company_admin_email=decoded_data["company_admin_email"],
    )
    return JSONResponse(response_data, status_code=status_code)
