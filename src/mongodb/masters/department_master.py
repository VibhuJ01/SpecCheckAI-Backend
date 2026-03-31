from datetime import datetime
from http import HTTPStatus
from typing import Any
from uuid import uuid4

import pytz
from pydantic import ValidationError

from src.enums import LogActionType, MongoCollectionsNames
from src.mongodb.base import BaseDatabase
from src.mongodb.log_manager import LogManager
from src.schema import DepartmentDetails


class DepartmentMaster:
    collection = BaseDatabase.get_collection(collection_name=MongoCollectionsNames.DEPARTMENT_MASTER)

    valid_date_formats = ["DDMMYYYY", "MMDDYYYY", "YYYYMMDD", "DDMMYY", "MMDDYY", "YYMMDD"]

    def add_department(
        self, request_data: dict[str, Any], current_user_email: str, company_admin_email: str
    ) -> tuple[dict[str, Any], int]:
        try:
            validated_request_data = DepartmentDetails.model_validate(request_data)
        except ValidationError:
            return {"is_successful": False, "message": "Invalid or incomplete request data."}, HTTPStatus.BAD_REQUEST

        if (
            validated_request_data.sample_date_format
            and validated_request_data.sample_date_format not in self.valid_date_formats
        ):
            return {
                "is_successful": False,
                "message": f"Invalid Sample Code Date Format. Valid formats are: {', '.join(self.valid_date_formats)}.",
            }, HTTPStatus.BAD_REQUEST

        data_to_insert = validated_request_data.model_dump(by_alias=True)
        data_to_insert.update(
            {
                "department_code": str(uuid4()),
                "customer_admin_code": company_admin_email,
                "created_at": datetime.now(pytz.utc),
                "updated_at": datetime.now(pytz.utc),
            }
        )

        result = self.collection.insert_one(data_to_insert)
        if not result.acknowledged:
            return {
                "is_successful": False,
                "message": "Failed to add the department. Please contact support!",
            }, HTTPStatus.INTERNAL_SERVER_ERROR

        LogManager.add_log(
            current_user_email=current_user_email,
            company_admin_email=company_admin_email,
            log_action_type=LogActionType.ADD,
            message=f"ADDED Department: {validated_request_data.department_name} ({data_to_insert['department_code']})",
        )

        return {"is_successful": True, "message": "Department Successfully Added."}, HTTPStatus.OK

    def edit_department(
        self, request_data: dict[str, Any], current_user_email: str, company_admin_email: str
    ) -> tuple[dict[str, Any], int]:

        try:
            validated_request_data = DepartmentDetails.model_validate(request_data)
        except ValidationError:
            return {"is_successful": False, "message": "Invalid or incomplete request data."}, HTTPStatus.BAD_REQUEST

        if (
            validated_request_data.sample_date_format
            and validated_request_data.sample_date_format not in self.valid_date_formats
        ):
            return {
                "is_successful": False,
                "message": f"Invalid Sample Code Date Format. Valid formats are: {', '.join(self.valid_date_formats)}.",
            }, HTTPStatus.BAD_REQUEST

        department_code = request_data["department_code"]
        update_data = validated_request_data.model_dump(by_alias=True)
        update_data["updated_at"] = datetime.now(pytz.utc)
        update_data["updated_by"] = current_user_email

        result = self.collection.update_one(
            {"department_code": department_code, "customer_admin_code": company_admin_email},
            {"$set": update_data},
        )

        if result.matched_count == 0:
            return {"is_successful": False, "message": "Department not found."}, HTTPStatus.NOT_FOUND
        if result.modified_count == 0:
            return {"is_successful": False, "message": "No changes made to the department."}, HTTPStatus.OK

        LogManager.add_log(
            current_user_email=current_user_email,
            company_admin_email=company_admin_email,
            log_action_type=LogActionType.EDIT,
            message=f"EDITED Department: {validated_request_data.department_name} ({department_code})",
        )

        return {"is_successful": True, "message": "Department Successfully Updated."}, HTTPStatus.OK

    def fetch_departments(self, company_admin_email: str) -> tuple[dict[str, Any], int]:
        departments = list(
            self.collection.find(
                {"customer_admin_code": company_admin_email},
                {"_id": 0, "department_code": 1, **{field: 1 for field in DepartmentDetails.model_fields}},
            )
        )

        return {
            "is_successful": True,
            "departments": departments,
            "message": "Departments fetched successfully.",
        }, HTTPStatus.OK
