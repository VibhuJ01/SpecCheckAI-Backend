from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any

from pydantic import ValidationError
from pymongo import ReturnDocument

from src.enums import MongoCollectionsNames, UserRoles
from src.mongodb.base import BaseDatabase
from src.mongodb.log_manager import LogActionType, LogManager
from src.schema import EmployeeDetails
from src.utils import create_user_and_send_email


class EmployeeMaster:

    collection = BaseDatabase.get_collection(collection_name=MongoCollectionsNames.USER_MASTER)
    company_collection = BaseDatabase.get_collection(collection_name=MongoCollectionsNames.COMPANY_MASTER)
    department_collection = BaseDatabase.get_collection(collection_name=MongoCollectionsNames.DEPARTMENT_MASTER)
    team_master_collection = BaseDatabase.get_collection(collection_name=MongoCollectionsNames.TEAM_MASTER)
    employee_signature_collection = BaseDatabase.get_collection(
        collection_name=MongoCollectionsNames.EMPLOYEE_SIGNATURES
    )

    def is_user_exists(self, email: str) -> bool:
        user_exists = self.collection.find_one({"email": email.lower()})
        return user_exists is not None

    def do_all_department_exists(self, department_codes: list[str], company_admin_email: str) -> bool:
        existing_departments_count = self.department_collection.count_documents(
            {"department_code": {"$in": department_codes}, "company_admin_email": company_admin_email}
        )
        return existing_departments_count == len(department_codes)

    def do_all_teams_exist(self, team_codes: list[str], company_admin_email: str) -> bool:
        existing_teams_count = self.team_master_collection.count_documents(
            {"team_code": {"$in": team_codes}, "company_admin_email": company_admin_email}
        )
        return existing_teams_count == len(team_codes)

    def add_employee(self, request_data: dict, current_user_email: str, company_admin_email: str) -> tuple[dict, int]:
        try:
            validated_request_data = EmployeeDetails.model_validate(request_data)
        except ValidationError:
            return {"is_successful": False, "message": "Invalid or incomplete request data."}, HTTPStatus.BAD_REQUEST

        if len(set(validated_request_data.department_codes)) != len(validated_request_data.department_codes):
            validated_request_data.department_codes = list(set(validated_request_data.department_codes))

        if not self.do_all_department_exists(validated_request_data.department_codes, company_admin_email):
            return {
                "is_successful": False,
                "message": f"One or more department codes are invalid. Please check and try again.",
            }, HTTPStatus.BAD_REQUEST

        if len(set(validated_request_data.team_codes)) != len(validated_request_data.team_codes):
            validated_request_data.team_codes = list(set(validated_request_data.team_codes))

        if not self.do_all_teams_exist(validated_request_data.team_codes, company_admin_email):
            return {
                "is_successful": False,
                "message": f"One or more team codes are invalid. Please check and try again.",
            }, HTTPStatus.BAD_REQUEST

        company = self.company_collection.find_one({"email": company_admin_email})
        if not company:
            return {"is_successful": False, "message": "Company not found."}, HTTPStatus.NOT_FOUND

        employee_access_limit = int(company.get("employee_access_limit", 0))  # 0 means 0 not unlimited

        # Count active employees for this company (exclude disabled)
        active_count = self.collection.count_documents(
            {"company_admin_email": company_admin_email, "role": UserRoles.EMPLOYEE.value, "is_disabled": False}
        )

        if active_count >= employee_access_limit:
            return {
                "is_successful": False,
                "message": f"Employee limit reached. Allowed: {employee_access_limit}, Active: {active_count}. Disable an employee or buy more license to add more employees.",
            }, HTTPStatus.BAD_REQUEST

        if self.is_user_exists(validated_request_data.email):
            return {
                "is_successful": False,
                "message": f"User with email '{validated_request_data.email}' already exists",
            }, HTTPStatus.BAD_REQUEST

        employee_data = validated_request_data.model_dump()

        extra_data = {
            "permissions": employee_data["permissions"],
            "company_admin_email": company_admin_email,
            "created_at": datetime.now(timezone.utc),
            "created_by": current_user_email,
            "department_codes": employee_data["department_codes"],
            "team_codes": employee_data["team_codes"],
        }

        user_creation = create_user_and_send_email(
            email=validated_request_data.email,
            name=validated_request_data.name,
            role=UserRoles.EMPLOYEE,
            created_by=current_user_email,
            phone_number=validated_request_data.phone_number,
            extra_data=extra_data,
        )

        if not user_creation["is_successful"]:
            self.collection.delete_one({"email": validated_request_data.email})  # Rollback if needed
            return {
                "is_successful": True,
                "message": f"Employee '{validated_request_data.name}' added. BUT: {user_creation['message']}",
            }, HTTPStatus.OK

        LogManager.add_log(
            current_user_email=current_user_email,
            company_admin_email=company_admin_email,
            log_action_type=LogActionType.ADD,
            message=f"ADDED a new employee: {validated_request_data.name}({validated_request_data.email})",
        )

        return {"is_successful": True, "message": "Employee added successfully"}, HTTPStatus.OK

    def update_employee(
        self, request_data: dict, current_user_email: str, company_admin_email: str
    ) -> tuple[dict, int]:

        try:
            validated_request_data = EmployeeDetails.model_validate(request_data)
        except ValidationError:
            return {"is_successful": False, "message": "Invalid or incomplete request data."}, HTTPStatus.BAD_REQUEST

        if len(set(validated_request_data.department_codes)) != len(validated_request_data.department_codes):
            validated_request_data.department_codes = list(set(validated_request_data.department_codes))

        if not self.do_all_department_exists(validated_request_data.department_codes, company_admin_email):
            return {
                "is_successful": False,
                "message": f"Department with codes '{validated_request_data.department_codes}' do not exist.",
            }, HTTPStatus.BAD_REQUEST

        if len(set(validated_request_data.team_codes)) != len(validated_request_data.team_codes):
            validated_request_data.team_codes = list(set(validated_request_data.team_codes))

        if not self.do_all_teams_exist(validated_request_data.team_codes, company_admin_email):
            return {
                "is_successful": False,
                "message": f"One or more team codes are invalid. Please check and try again.",
            }, HTTPStatus.BAD_REQUEST

        update_data = validated_request_data.model_dump()
        employee_email = update_data.pop("email")

        update_data["updated_by"] = current_user_email
        update_data["updated_at"] = datetime.now(timezone.utc)

        result = self.collection.find_one_and_update(
            {"email": employee_email.lower(), "company_admin_email": company_admin_email},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER,
        )

        if result:
            LogManager.add_log(
                current_user_email=current_user_email,
                company_admin_email=company_admin_email,
                log_action_type=LogActionType.EDIT,
                message=f"UPDATED employee details: {result['name']}({result['email']})",
            )
            return {"is_successful": True, "message": "Employee updated successfully"}, HTTPStatus.OK

        return {"is_successful": False, "message": "Employee not found"}, HTTPStatus.NOT_FOUND

    def fetch_all_employees(self, company_admin_email: str) -> tuple[dict, int]:

        users = list(
            self.collection.find(
                {"role": UserRoles.EMPLOYEE.value, "company_admin_email": company_admin_email},
                {"_id": 0, "is_disabled": 1, "code": 1, **{field: 1 for field in EmployeeDetails.model_fields}},
            )
        )

        return {
            "is_successful": True,
            "user_data": users,
            "message": "Successfully Fetched the Data!",
        }, HTTPStatus.OK

    def disable_employee(
        self, disable_user_email: str, current_user_email: str, company_admin_email: str
    ) -> tuple[dict, int]:
        if disable_user_email.lower() == current_user_email.lower():
            return {
                "is_successful": False,
                "message": "You can't disable yourself.",
            }, HTTPStatus.FORBIDDEN

        user_to_disable = self.collection.find_one({"email": disable_user_email.lower(), "is_disabled": False})

        if not user_to_disable:
            return {
                "is_successful": False,
                "message": f"Employee with email '{disable_user_email}' not found or is already disabled.",
            }, HTTPStatus.NOT_FOUND

        result = self.collection.update_one(
            {
                "email": disable_user_email.lower(),
                "role": UserRoles.EMPLOYEE.value,
                "company_admin_email": company_admin_email,
            },
            {"$set": {"is_disabled": True}},
        )

        if result.matched_count == 0:
            return {
                "is_successful": False,
                "message": "Failed to disable the employee. Invalid email.",
            }, HTTPStatus.BAD_REQUEST

        LogManager.add_log(
            current_user_email=current_user_email,
            company_admin_email=company_admin_email,
            log_action_type=LogActionType.DISABLE,
            message=f"DISABLED employee: {user_to_disable['name']}({user_to_disable['email']})",
        )

        return {
            "is_successful": True,
            "message": f"Employee with '{disable_user_email}' has been disabled.",
        }, HTTPStatus.OK

    def enable_employee(self, enable_user_email: str, company_admin_email: str) -> tuple[dict, int]:
        user_to_enable = self.collection.find_one({"email": enable_user_email.lower(), "is_disabled": True})

        if not user_to_enable:
            return {
                "is_successful": False,
                "message": f"Either Employee with email '{enable_user_email}' not found or is already enabled/active.",
            }, HTTPStatus.NOT_FOUND

        company = self.company_collection.find_one({"email": company_admin_email})
        if not company:
            return {"is_successful": False, "message": "Company not found."}, HTTPStatus.NOT_FOUND

        employee_access_limit = int(company.get("employee_access_limit", 0))

        active_count = self.collection.count_documents(
            {"company_admin_email": company_admin_email, "role": UserRoles.EMPLOYEE.value, "is_disabled": False}
        )
        # If enabling this user would exceed limit, deny
        if active_count >= employee_access_limit:
            return {
                "is_successful": False,
                "message": f"Cannot enable employee. Employee limit reached ({employee_access_limit}). Active: {active_count}.",
            }, HTTPStatus.BAD_REQUEST

        result = self.collection.update_one(
            {
                "email": enable_user_email.lower(),
                "role": UserRoles.EMPLOYEE.value,
                "company_admin_email": company_admin_email,
            },
            {"$set": {"is_disabled": False}},
        )

        if result.matched_count == 0:
            return {
                "is_successful": False,
                "message": "Failed to enable the employee.",
            }, HTTPStatus.BAD_REQUEST

        LogManager.add_log(
            current_user_email=company_admin_email,
            company_admin_email=company_admin_email,
            log_action_type=LogActionType.ENABLE,
            message=f"ENABLED employee: {user_to_enable['name']}({user_to_enable['email']})",
        )

        return {
            "is_successful": True,
            "message": f"Employee with email '{enable_user_email}' has been enabled.",
        }, HTTPStatus.OK

    # ───────────────────── Employee Signature ─────────────────────

    def _validate_signature_fields(self, designation: str, dept_team_name: str) -> tuple[bool, str]:
        if len(designation) > 50:
            return False, "Designation cannot exceed 50 characters."
        if len(dept_team_name) > 50:
            return False, "Department or team name cannot exceed 50 characters."
        return True, ""

    def upsert_employee_signature(
        self,
        employee_email: str,
        designation: str,
        dept_team_name: str,
        current_user_email: str,
        company_admin_email: str,
        signature_file: Any = None,
    ) -> tuple[dict, int]:
        employee_email = employee_email.lower()

        if not self.collection.find_one({"email": employee_email, "company_admin_email": company_admin_email}):
            return {"is_successful": False, "message": "Employee not found."}, HTTPStatus.NOT_FOUND

        valid, msg = self._validate_signature_fields(designation, dept_team_name)
        if not valid:
            return {"is_successful": False, "message": msg}, HTTPStatus.BAD_REQUEST

        now = datetime.now(timezone.utc)
        set_data = {
            "designation": designation,
            "dept_team_name": dept_team_name,
            "updated_at": now,
            "updated_by": current_user_email,
        }

        try:
            from src.mongodb.general_config import GeneralConfigManager

            set_data["signature_data"] = GeneralConfigManager().save_image_to_base64(signature_file)
        except ValueError as ve:
            return {"is_successful": False, "message": f"Invalid signature file: {str(ve)}"}, HTTPStatus.BAD_REQUEST

        except Exception as e:
            return {
                "is_successful": False,
                "message": f"An error occurred while processing the signature file.",
            }, HTTPStatus.INTERNAL_SERVER_ERROR

        result = self.employee_signature_collection.update_one(
            {"employee_email": employee_email, "company_admin_email": company_admin_email},
            {
                "$set": set_data,
                "$setOnInsert": {
                    "employee_email": employee_email,
                    "company_admin_email": company_admin_email,
                    "created_at": now,
                    "created_by": current_user_email,
                },
            },
            upsert=True,
        )

        is_insert = result.upserted_id is not None
        LogManager.add_log(
            current_user_email=current_user_email,
            company_admin_email=company_admin_email,
            log_action_type=LogActionType.ADD if is_insert else LogActionType.EDIT,
            message=f"{'ADDED' if is_insert else 'UPDATED'} employee signature for {employee_email}.",
        )

        msg = "Employee signature added successfully." if is_insert else "Employee signature updated successfully."
        return {"is_successful": True, "message": msg}, HTTPStatus.OK

    def fetch_employee_signature(self, employee_email: str, company_admin_email: str) -> tuple[dict, int]:
        try:
            record = self.employee_signature_collection.find_one(
                {"employee_email": employee_email.lower(), "company_admin_email": company_admin_email},
                {"_id": 0, "employee_email": 1, "designation": 1, "dept_team_name": 1, "signature_data": 1},
            )

            if record:
                return (
                    {"is_successful": True, **record, "message": "Employee signature fetched successfully."},
                    HTTPStatus.OK,
                )

            return (
                {"is_successful": False, "message": "Employee signature not found."},
                HTTPStatus.NOT_FOUND,
            )
        except Exception as e:
            return (
                {"is_successful": False, "message": f"An error occurred while fetching employee signature: {str(e)}"},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def delete_employee_signature(
        self, employee_email: str, current_user_email: str, company_admin_email: str
    ) -> tuple[dict, int]:
        try:
            result = self.employee_signature_collection.delete_one(
                {"employee_email": employee_email.lower(), "company_admin_email": company_admin_email}
            )

            if result.deleted_count > 0:
                LogManager.add_log(
                    current_user_email=current_user_email,
                    company_admin_email=company_admin_email,
                    log_action_type=LogActionType.DELETE,
                    message=f"DELETED employee signature for {employee_email.lower()}.",
                )
                return {"is_successful": True, "message": "Employee signature deleted successfully."}, HTTPStatus.OK

            return (
                {"is_successful": False, "message": "Employee signature not found."},
                HTTPStatus.NOT_FOUND,
            )
        except Exception as e:
            return (
                {"is_successful": False, "message": f"An error occurred while deleting employee signature: {str(e)}"},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
