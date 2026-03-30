import logging as logger
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any

from pydantic import ValidationError

from src.enums import LogActionType, MongoCollectionsNames
from src.mongodb.base import BaseDatabase
from src.mongodb.log_manager import LogManager
from src.schema import ClientDetails


class ClientMaster:

    collection = BaseDatabase.get_collection(collection_name=MongoCollectionsNames.CLIENT_MASTER)

    def add_client(
        self, request_data: dict, current_user_email: str, company_admin_email: str
    ) -> tuple[dict[str, Any], int]:
        """Add a new client record to the database."""

        try:
            validated_data = ClientDetails.model_validate(request_data)
        except ValidationError as e:
            logger.exception("Validation error while adding client", e)
            return {"is_successful": False, "message": "Invalid or incomplete request data."}, HTTPStatus.BAD_REQUEST

        if not validated_data.email:
            return {
                "is_successful": False,
                "message": "Email is required for client creation.",
            }, HTTPStatus.BAD_REQUEST

        validated_data.email = validated_data.email.lower()

        # Check if client with this email already exists for this company admin
        if self.collection.find_one({"email": validated_data.email, "company_admin_email": company_admin_email}):
            return {
                "is_successful": False,
                "message": f"Client with email '{validated_data.email}' already exists.",
            }, HTTPStatus.CONFLICT

        client_code = str(uuid.uuid4())
        client_data = validated_data.model_dump()

        client_data.update(
            {
                "client_code": client_code,
                "company_admin_email": company_admin_email,
                "created_at": datetime.now(timezone.utc),
                "created_by": current_user_email,
            }
        )

        result = self.collection.insert_one(client_data)
        if not result.acknowledged:
            return {
                "is_successful": False,
                "message": "Failed to add client to the database. Please try again.",
            }, HTTPStatus.INTERNAL_SERVER_ERROR

        LogManager.add_log(
            current_user_email=current_user_email,
            company_admin_email=company_admin_email,
            log_action_type=LogActionType.ADD,
            message=f"ADDED client details: {validated_data.name}({validated_data.email})",
        )

        return {
            "is_successful": True,
            "message": f"Client '{validated_data.legal_name}' added successfully.",
        }, HTTPStatus.OK

    def update_client(
        self, request_data: dict, current_user_email: str, company_admin_email: str
    ) -> tuple[dict[str, Any], int]:
        """Update existing client details."""

        try:
            validated_data = ClientDetails.model_validate(request_data)
        except ValidationError as e:
            logger.exception("Validation error while updating client", e)
            return {"is_successful": False, "message": "Invalid or incomplete request data."}, HTTPStatus.BAD_REQUEST

        client_code = request_data.get("client_code")
        if not client_code:
            return {"is_successful": False, "message": "Missing required field: client_code"}, HTTPStatus.BAD_REQUEST

        existing_client = self.collection.find_one(
            {"client_code": client_code, "company_admin_email": company_admin_email}
        )
        if not existing_client:
            return {
                "is_successful": False,
                "message": f"Client with code '{client_code}' not found.",
            }, HTTPStatus.NOT_FOUND

        updated_data = validated_data.model_dump()
        updated_data.pop("client_code", None)
        updated_data["email"] = existing_client["email"]  # Prevent email update

        updated_data.update(
            {
                "updated_at": datetime.now(timezone.utc),
                "updated_by": current_user_email,
            }
        )

        result = self.collection.update_one(
            {"client_code": client_code, "company_admin_email": company_admin_email},
            {"$set": updated_data},
        )

        if result.matched_count == 0:
            return {
                "is_successful": False,
                "message": "Failed to find the client to update.",
            }, HTTPStatus.NOT_FOUND

        if result.modified_count == 0:
            return {
                "is_successful": True,
                "message": "No changes were made to the client details.",
            }, HTTPStatus.OK

        LogManager.add_log(
            current_user_email=current_user_email,
            company_admin_email=company_admin_email,
            log_action_type=LogActionType.EDIT,
            message=f"UPDATED client details: {validated_data.name}({validated_data.email})",
        )

        return {
            "is_successful": True,
            "message": f"Client '{validated_data.legal_name}' updated successfully.",
        }, HTTPStatus.OK

    def fetch_all_clients(self, company_admin_email: str) -> tuple[dict[str, Any], int]:
        """Fetch all clients for a specific company admin."""

        clients = list(
            self.collection.find(
                {"company_admin_email": company_admin_email},
                {
                    "_id": 0,
                    "client_code": 1,
                    **{field: 1 for field in ClientDetails.model_fields},
                },
            )
        )

        return {
            "is_successful": True,
            "clients": clients,
        }, HTTPStatus.OK

    def delete_client(
        self, client_code: str, current_user_email: str, company_admin_email: str
    ) -> tuple[dict[str, Any], int]:
        """Delete a client record."""

        result = self.collection.delete_one({"client_code": client_code, "company_admin_email": company_admin_email})

        if result.deleted_count == 0:
            return {
                "is_successful": False,
                "message": f"Client with code '{client_code}' not found.",
            }, HTTPStatus.NOT_FOUND

        LogManager.add_log(
            current_user_email=current_user_email,
            company_admin_email=company_admin_email,
            log_action_type=LogActionType.DELETE,
            message=f"DELETED client details: {client_code}",
        )

        return {
            "is_successful": True,
            "message": "Client deleted successfully.",
        }, HTTPStatus.OK

    def download_client_as_csv(self, company_admin_email: str) -> tuple[dict[str, Any], int]:
        """Download all client details as a CSV file. All fields"""

        clients = list(
            self.collection.find(
                {"company_admin_email": company_admin_email},
                {
                    "_id": 0,
                    "client_code": 1,
                    **{field: 1 for field in ClientDetails.model_fields},
                },
            )
        )
        if not clients:
            return {
                "is_successful": False,
                "message": "No clients found to download.",
            }, HTTPStatus.NOT_FOUND

        csv_data = []
        header = list(ClientDetails.model_fields.keys())
        csv_data.append(header)
        for client in clients:
            row = []
            for field in ClientDetails.model_fields.keys():
                row.append(client.get(field, ""))
            csv_data.append(row)

        csv_string = ""
        for row in csv_data:
            csv_string += ",".join(str(value).replace('"', '""') for value in row) + "\n"

        return {
            "is_successful": True,
            "csv_data": csv_string,
        }, HTTPStatus.OK
