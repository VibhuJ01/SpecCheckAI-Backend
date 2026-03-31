import logging as logger
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any

from pydantic import ValidationError

from src.enums import (
    LogActionType,
    MongoCollectionsNames,
    StandardLimitType,
    TeamLabAnalystType,
)
from src.mongodb.base import BaseDatabase
from src.mongodb.log_manager import LogManager
from src.schema import SpecificationMatrixDetails, StandardInSpecificationRequest


class SpecificationMatrixMaster:

    collection = BaseDatabase.get_collection(collection_name=MongoCollectionsNames.SPECIFICATION_MATRIX)
    standard_master_collection = BaseDatabase.get_collection(collection_name=MongoCollectionsNames.STANDARD_MASTER)
    team_master_collection = BaseDatabase.get_collection(collection_name=MongoCollectionsNames.TEAM_MASTER)
    user_master_collection = BaseDatabase.get_collection(collection_name=MongoCollectionsNames.USER_MASTER)

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
                "message": f"Specification matrix not found.",
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

    def delete_specification_matrix(
        self, code: str, current_user_email: str, company_admin_email: str
    ) -> tuple[dict[str, Any], int]:
        """Delete a specification matrix record from the database."""

        result = self.collection.delete_one({"code": code, "company_admin_email": company_admin_email})
        if result.deleted_count == 0:
            return {
                "is_successful": False,
                "message": f"Specification matrix not found or already deleted.",
            }, HTTPStatus.NOT_FOUND

        LogManager.add_log(
            current_user_email=current_user_email,
            company_admin_email=company_admin_email,
            log_action_type=LogActionType.DELETE,
            message=f"DELETED specification matrix with code: {code}",
        )

        return {
            "is_successful": True,
            "message": f"Specification matrix deleted successfully.",
        }, HTTPStatus.OK

    def add_standard(
        self, current_user_email: str, standard_data: dict[str, Any], company_admin_email: str
    ) -> tuple[dict[str, Any], int]:
        try:
            standard_data_schema = StandardInSpecificationRequest.model_validate(standard_data)
        except ValidationError as e:
            return {
                "is_successful": False,
                "message": "Incomplete or Invalid request data.",
            }, HTTPStatus.BAD_REQUEST

        if standard_data_schema.limit_type == StandardLimitType.RANGE:
            if standard_data_schema.standard_limit_min is None or standard_data_schema.standard_limit_max is None:
                return {
                    "is_successful": False,
                    "message": "For RANGE limit type, both 'standard_limit_min' and 'standard_limit_max' must be provided.",
                }, HTTPStatus.BAD_REQUEST

            if standard_data_schema.standard_limit_min >= standard_data_schema.standard_limit_max:
                return {
                    "is_successful": False,
                    "message": "'standard_limit_min' must be less than 'standard_limit_max' for RANGE limit type.",
                }, HTTPStatus.BAD_REQUEST

        elif standard_data_schema.limit_type == StandardLimitType.MAX:
            if standard_data_schema.standard_limit_max is None:
                return {
                    "is_successful": False,
                    "message": "For MAX limit type, 'standard_limit_max' must be provided.",
                }, HTTPStatus.BAD_REQUEST

        elif standard_data_schema.limit_type == StandardLimitType.MIN:
            if standard_data_schema.standard_limit_min is None:
                return {
                    "is_successful": False,
                    "message": "For MIN limit type, 'standard_limit_min' must be provided.",
                }, HTTPStatus.BAD_REQUEST

        specification_data = self.collection.find_one(
            {"code": standard_data_schema.specification_code, "company_admin_email": company_admin_email}
        )

        if not specification_data:
            return {
                "is_successful": False,
                "message": f"Specification not found.",
            }, HTTPStatus.NOT_FOUND

        if standard_data_schema.team_lab_analyst_type == TeamLabAnalystType.TEAM:
            team_data = self.team_master_collection.find_one(
                {"team_name": standard_data_schema.team_lab_analyst, "company_admin_email": company_admin_email}
            )
            if not team_data:
                return {
                    "is_successful": False,
                    "message": f"Please enter a valid Team Name.",
                }, HTTPStatus.BAD_REQUEST

            standard_data_schema.team_lab_analyst = team_data["team_code"]

        elif standard_data_schema.team_lab_analyst_type == TeamLabAnalystType.EMPLOYEE:
            employee_data = self.user_master_collection.find_one(
                {"email": standard_data_schema.team_lab_analyst, "company_admin_email": company_admin_email}
            )

            if not employee_data:
                return {
                    "is_successful": False,
                    "message": f"Please enter a valid Team Lab Analyst Email.",
                }, HTTPStatus.BAD_REQUEST
            standard_data_schema.team_lab_analyst = employee_data["email"]

        else:
            standard_data_schema.team_lab_analyst = ""

        result = self.standard_master_collection.insert_one(
            {
                **standard_data_schema.model_dump(),
                "standard_code": str(uuid.uuid4()),
                "company_admin_email": company_admin_email,
                "created_at": datetime.now(timezone.utc),
                "created_by": current_user_email,
            }
        )
        if not result.acknowledged:
            return {"is_successful": False, "message": "Failed to add new standard."}, HTTPStatus.INTERNAL_SERVER_ERROR

        LogManager.add_log(
            current_user_email=current_user_email,
            company_admin_email=company_admin_email,
            log_action_type=LogActionType.ADD,
            message=f"ADDED Standard: '{standard_data_schema.standard_name}' in Specification Matrix.",
        )

        return {"is_successful": True, "message": "New standard successfully added."}, HTTPStatus.OK

    def edit_standard(
        self, current_user_email: str, request_data: dict[str, Any], company_admin_email: str
    ) -> tuple[dict[str, Any], int]:

        try:
            standard_data_schema = StandardInSpecificationRequest.model_validate(request_data)
        except ValidationError as e:
            return {
                "is_successful": False,
                "message": "Incomplete or Invalid request data.",
            }, HTTPStatus.BAD_REQUEST

        if standard_data_schema.limit_type == StandardLimitType.RANGE:
            if standard_data_schema.standard_limit_min is None or standard_data_schema.standard_limit_max is None:
                return {
                    "is_successful": False,
                    "message": "For RANGE limit type, both 'standard_limit_min' and 'standard_limit_max' must be provided.",
                }, HTTPStatus.BAD_REQUEST

            if standard_data_schema.standard_limit_min >= standard_data_schema.standard_limit_max:
                return {
                    "is_successful": False,
                    "message": "'standard_limit_min' must be less than 'standard_limit_max' for RANGE limit type.",
                }, HTTPStatus.BAD_REQUEST

        elif standard_data_schema.limit_type == StandardLimitType.MAX:
            if standard_data_schema.standard_limit_max is None:
                return {
                    "is_successful": False,
                    "message": "For MAX limit type, 'standard_limit_max' must be provided.",
                }, HTTPStatus.BAD_REQUEST

        elif standard_data_schema.limit_type == StandardLimitType.MIN:
            if standard_data_schema.standard_limit_min is None:
                return {
                    "is_successful": False,
                    "message": "For MIN limit type, 'standard_limit_min' must be provided.",
                }, HTTPStatus.BAD_REQUEST

        standard_code = request_data["standard_code"]
        standard_record = self.standard_master_collection.find_one(
            {
                "standard_code": standard_code,
                "company_admin_email": company_admin_email,
            }
        )
        if not standard_record:
            return {
                "is_successful": False,
                "message": f"Standard not found.",
            }, HTTPStatus.NOT_FOUND

        standard_data_schema.specification_code = standard_record[
            "specification_code"
        ]  # Ensure the specification code is not changed during edit

        if standard_data_schema.team_lab_analyst_type == TeamLabAnalystType.TEAM:
            team_data = self.team_master_collection.find_one(
                {"team_name": standard_data_schema.team_lab_analyst, "company_admin_email": company_admin_email}
            )
            if not team_data:
                return {
                    "is_successful": False,
                    "message": f"Please enter a valid Team Name.",
                }, HTTPStatus.BAD_REQUEST

            standard_data_schema.team_lab_analyst = team_data["team_code"]

        elif standard_data_schema.team_lab_analyst_type == TeamLabAnalystType.EMPLOYEE:
            employee_data = self.user_master_collection.find_one(
                {"email": standard_data_schema.team_lab_analyst, "company_admin_email": company_admin_email}
            )

            if not employee_data:
                return {
                    "is_successful": False,
                    "message": f"Please enter a valid Team Lab Analyst Email.",
                }, HTTPStatus.BAD_REQUEST
            standard_data_schema.team_lab_analyst = employee_data["email"]

        else:
            standard_data_schema.team_lab_analyst = ""

        result = self.standard_master_collection.update_one(
            {
                "standard_code": standard_code,
                "company_admin_email": company_admin_email,
            },
            {
                "$set": {
                    **standard_data_schema.model_dump(),
                    "updated_at": datetime.now(timezone.utc),
                    "updated_by": current_user_email,
                }
            },
        )

        if result.matched_count == 0:
            return {
                "is_successful": False,
                "message": "Failed to find the standard to update.",
            }, HTTPStatus.NOT_FOUND

        if result.modified_count == 0:
            return {
                "is_successful": True,
                "message": "No changes were made to the standard details.",
            }, HTTPStatus.OK

        LogManager.add_log(
            current_user_email=current_user_email,
            company_admin_email=company_admin_email,
            log_action_type=LogActionType.EDIT,
            message=f"EDITED Standard: '{standard_data_schema.standard_name}' in Specification Matrix.",
        )

        return {"is_successful": True, "message": "Standard details updated successfully."}, HTTPStatus.OK

    def fetch_standards_in_specification(
        self, specification_code: str, company_admin_email: str
    ) -> tuple[dict[str, Any], int]:

        standards = list(
            self.standard_master_collection.find(
                {"specification_code": specification_code, "company_admin_email": company_admin_email},
                {
                    "_id": 0,
                    "standard_code": 1,
                    **{
                        field: 1
                        for field in StandardInSpecificationRequest.model_fields
                        if field != "specification_code"
                    },
                },
            )
        )

        return {
            "is_successful": True,
            "standards": standards,
        }, HTTPStatus.OK

    def delete_standard(
        self, standard_code: str, current_user_email: str, company_admin_email: str
    ) -> tuple[dict[str, Any], int]:
        result = self.standard_master_collection.delete_one(
            {"standard_code": standard_code, "company_admin_email": company_admin_email}
        )
        if result.deleted_count == 0:
            return {
                "is_successful": False,
                "message": f"Standard not found or already deleted.",
            }, HTTPStatus.NOT_FOUND

        LogManager.add_log(
            current_user_email=current_user_email,
            company_admin_email=company_admin_email,
            log_action_type=LogActionType.DELETE,
            message=f"DELETED Standard from Specification Matrix.",
        )

        return {
            "is_successful": True,
            "message": f"Standard  deleted successfully.",
        }, HTTPStatus.OK
