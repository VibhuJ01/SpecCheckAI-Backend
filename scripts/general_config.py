import base64
from http import HTTPStatus
from io import BytesIO

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from src.enums import MongoCollectionsNames
from src.mongodb.general_config import GeneralConfigManager
from src.utils import (
    employee_edit_permission,
    employee_page_permission,
    requires_verification,
)

router = APIRouter()
general_config_manager = GeneralConfigManager()


@router.post("/upsert_smtp_details")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.GENERAL_CONFIG)
async def upsert_smtp_details(request: Request, decoded_data: dict = {}):
    request_data = await request.json()
    response_data, status_code = general_config_manager.upsert_smtp_details(
        current_user_email=decoded_data["email"],
        smtp_details=request_data,
        company_admin_email=decoded_data["company_admin_email"],
    )
    return JSONResponse(response_data, status_code=status_code)


@router.get("/fetch_smtp_email")
@requires_verification
@employee_page_permission(page_name=MongoCollectionsNames.GENERAL_CONFIG)
async def fetch_smtp_email(request: Request, decoded_data: dict = {}):
    response_data, status_code = general_config_manager.fetch_smtp_email(
        company_admin_email=decoded_data["company_admin_email"]
    )
    return JSONResponse(response_data, status_code=status_code)


@router.delete("/delete_smtp_details")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.GENERAL_CONFIG)
async def delete_smtp_details(request: Request, decoded_data: dict = {}):
    response_data, status_code = general_config_manager.delete_smtp_details(
        current_user_email=decoded_data["email"],
        company_admin_email=decoded_data["company_admin_email"],
    )
    return JSONResponse(response_data, status_code=status_code)


@router.post("/upsert_image")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.GENERAL_CONFIG)
async def upsert_image(
    request: Request,
    image_type: str = Form(..., description="Type of image: logo, signature, or stamp"),
    image_file: UploadFile = File(..., description="Image file to upload"),
    decoded_data: dict = {},
):
    response_data, status_code = general_config_manager.upsert_image(
        current_user_email=decoded_data["email"],
        company_admin_email=decoded_data["company_admin_email"],
        image_type=image_type,
        image_file=image_file,
    )
    return JSONResponse(response_data, status_code=status_code)


@router.get("/get_image_data")
@requires_verification
@employee_page_permission(page_name=MongoCollectionsNames.GENERAL_CONFIG)
async def get_image_data(
    request: Request,
    image_type: str = Query(..., description="Type of image: logo, signature, or stamp"),
    decoded_data: dict = {},
):

    response_data, status_code = general_config_manager.get_image_data(
        company_admin_email=decoded_data["company_admin_email"],
        image_type=image_type,
    )

    if status_code != HTTPStatus.OK:
        return JSONResponse(response_data, status_code=status_code)

    base64_data = response_data["data"]
    try:
        if base64_data.startswith("data:"):
            header, encoded = base64_data.split(",", 1)
            mime_type = header.split(";")[0].replace("data:", "")
        else:
            mime_type = "image/png"
            encoded = base64_data

        image_bytes = base64.b64decode(encoded)

        file_extension = mime_type.split("/")[-1]
        if file_extension == "jpeg":
            file_extension = "jpg"

        return StreamingResponse(
            BytesIO(image_bytes),
            media_type=mime_type,
            headers={"Content-Disposition": f'inline; filename="{image_type}.{file_extension}"'},
        )
    except Exception as e:
        return JSONResponse(
            {
                "is_successful": False,
                "message": f"Error decoding image data: {str(e)}",
            },
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        )


@router.delete("/delete_image")
@requires_verification
@employee_edit_permission(page_name=MongoCollectionsNames.GENERAL_CONFIG)
async def delete_image(
    request: Request,
    image_type: str = Query(..., description="Type of image: logo, signature, or stamp"),
    decoded_data: dict = {},
):
    response_data, status_code = general_config_manager.delete_image(
        current_user_email=decoded_data["email"],
        company_admin_email=decoded_data["company_admin_email"],
        image_type=image_type,
    )
    return JSONResponse(response_data, status_code=status_code)
