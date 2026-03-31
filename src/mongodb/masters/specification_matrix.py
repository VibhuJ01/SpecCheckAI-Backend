import logging as logger
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any

from pydantic import ValidationError

from src.enums import LogActionType, MongoCollectionsNames
from src.mongodb.base import BaseDatabase
from src.mongodb.log_manager import LogManager
from src.schema import SpecificationMatrixDetails


class SpecificationMatrixMaster:

    collection = BaseDatabase.get_collection(collection_name=MongoCollectionsNames.SPECIFICATION_MATRIX)

    def add_specification_matrix(
        self, request_data: dict, current_user_email: str, company_admin_email: str
    ) -> tuple[dict[str, Any], int]:
        """Add a new specification matrix record to the database."""

        try:
            validated_data = SpecificationMatrixDetails.model_validate(request_data)
        except ValidationError as e:
            logger.exception("Validation error while adding specification matrix", e)
            return {"is_successful": False, "message": "Invalid or incomplete request data."}, HTTPStatus.BAD_REQUEST

        code = str(uuid.uuid4())
        specification_matrix_data = validated_data.model_dump()

        specification_matrix_data.update(
            {
                "code": code,
                "company_admin_email": company_admin_email,
                "created_at": datetime.now(timezone.utc),
                "created_by": current_user_email,
                "do_standards_exist": False,
            }
        )

        result = self.collection.insert_one(specification_matrix_data)
        if not result.acknowledged:
            return {
                "is_successful": False,
                "message": "Failed to add specification matrix to the database. Please try again.",
            }, HTTPStatus.INTERNAL_SERVER_ERROR

        LogManager.add_log(
            current_user_email=current_user_email,
            company_admin_email=company_admin_email,
            log_action_type=LogActionType.ADD,
            message=f"ADDED specification matrix: {validated_data.product_name}",
        )

        return {
            "is_successful": True,
            "message": f"Specification matrix '{validated_data.product_name}' added successfully.",
        }, HTTPStatus.OK

    def update_specification_matrix(
        self, request_data: dict, current_user_email: str, company_admin_email: str
    ) -> tuple[dict[str, Any], int]:
        """Update existing specification matrix details."""

        try:
            validated_data = SpecificationMatrixDetails.model_validate(request_data)
        except ValidationError as e:
            logger.exception("Validation error while updating specification matrix", e)
            return {"is_successful": False, "message": "Invalid or incomplete request data."}, HTTPStatus.BAD_REQUEST

        code = request_data["code"]
        existing_specification_matrix = self.collection.find_one(
            {
                "code": code,
                "company_admin_email": company_admin_email,
            }
        )
        if not existing_specification_matrix:
            return {
                "is_successful": False,
                "message": f"Specification matrix with code '{code}' not found.",
            }, HTTPStatus.NOT_FOUND

        updated_data = validated_data.model_dump()
        updated_data.update(
            {
                "updated_at": datetime.now(timezone.utc),
                "updated_by": current_user_email,
            }
        )

        result = self.collection.update_one(
            {
                "code": code,
                "company_admin_email": company_admin_email,
            },
            {"$set": updated_data},
        )

        if result.matched_count == 0:
            return {
                "is_successful": False,
                "message": "Failed to find the specification matrix to update.",
            }, HTTPStatus.NOT_FOUND

        if result.modified_count == 0:
            return {
                "is_successful": True,
                "message": "No changes were made to the specification matrix details.",
            }, HTTPStatus.OK

        LogManager.add_log(
            current_user_email=current_user_email,
            company_admin_email=company_admin_email,
            log_action_type=LogActionType.EDIT,
            message=f"UPDATED specification matrix: {validated_data.product_name}",
        )

        return {
            "is_successful": True,
            "message": f"Specification matrix '{validated_data.product_name}' updated successfully.",
        }, HTTPStatus.OK

    def fetch_all_specification_matrix(self, company_admin_email: str) -> tuple[dict[str, Any], int]:
        """Fetch all specification matrix rows for a specific company admin."""

        specification_matrix_rows = list(
            self.collection.find(
                {"company_admin_email": company_admin_email},
                {
                    "_id": 0,
                    "code": 1,
                    "product_name": 1,
                    "product_description": 1,
                    "product_category": 1,
                },
            )
        )

        return {
            "is_successful": True,
            "specifications": specification_matrix_rows,
        }, HTTPStatus.OK
