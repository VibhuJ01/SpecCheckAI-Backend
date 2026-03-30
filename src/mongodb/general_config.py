import base64
from http import HTTPStatus
from typing import Any

from PIL import Image

from src.encryption_system import EncryptionSystem
from src.enums import LogActionType, MongoCollectionsNames
from src.mongodb.base import BaseDatabase
from src.mongodb.log_manager import LogManager


class GeneralConfigManager:
    collection = BaseDatabase.get_collection(collection_name=MongoCollectionsNames.GENERAL_CONFIG)
    MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB
    REQUIRED_DIMENSIONS = (500, 500)
    VALID_IMAGE_TYPES = {"logo", "signature", "stamp"}

    @staticmethod
    def _validate_image_type(image_type: str) -> dict:
        """Validate if the image_type is allowed."""
        if image_type not in GeneralConfigManager.VALID_IMAGE_TYPES:
            return {
                "is_successful": False,
                "message": f"Invalid image type. Must be one of: {', '.join(GeneralConfigManager.VALID_IMAGE_TYPES)}",
            }

        return {"is_successful": True}

    def upsert_smtp_details(
        self, current_user_email: str, smtp_details: dict, company_admin_email: str
    ) -> tuple[dict, int]:

        try:
            # Validate required fields
            if not all(key in smtp_details for key in ["email", "password", "provider"]):
                return (
                    {
                        "is_successful": False,
                        "message": "Missing required fields: email, password, and provider are required.",
                    },
                    HTTPStatus.BAD_REQUEST,
                )

            email = smtp_details["email"]
            provider = smtp_details["provider"]

            if len(email) > 300:
                return (
                    {
                        "is_successful": False,
                        "message": "Email can't be more than 300 characters.",
                    },
                    HTTPStatus.BAD_REQUEST,
                )

            if provider not in {"gmail", "outlook"}:
                return (
                    {
                        "is_successful": False,
                        "message": "Invalid provider. Must be 'gmail' or 'outlook'.",
                    },
                    HTTPStatus.BAD_REQUEST,
                )

            encrytion_system = EncryptionSystem()
            details = {
                "email": email.lower(),
                "password": smtp_details["password"],
                "provider": provider,
            }
            smtp_details_encrypted = encrytion_system.encrypt_dict(input_json=details)

            result = self.collection.update_one(
                {"company_admin_email": company_admin_email},
                {"$set": {"smtp_details": smtp_details_encrypted}},
                upsert=True,
            )

            # Handle insertion (upsert)
            if result.modified_count > 0 or result.upserted_id is not None:
                LogManager.add_log(
                    current_user_email=current_user_email,
                    company_admin_email=company_admin_email,
                    log_action_type=LogActionType.EDIT,
                    message="EDITED SMTP Details.",
                )
                return {"is_successful": True, "message": "SMTP Details successfully updated."}, HTTPStatus.OK

            # If no changes were made
            return (
                {
                    "is_successful": True,
                    "message": "No changes were made.",
                },
                HTTPStatus.OK,
            )
        except Exception as e:
            return (
                {
                    "is_successful": False,
                    "message": f"An error occurred while upserting SMTP details: {str(e)}",
                },
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def fetch_smtp_email(self, company_admin_email: str) -> tuple[dict, int]:

        try:
            document = self.collection.find_one(
                {"company_admin_email": company_admin_email}, {"smtp_details": 1, "_id": 0}
            )

            if document and "smtp_details" in document:
                encrytion_system = EncryptionSystem()
                smtp_details = encrytion_system.decrypt_string(encrypted_string=document["smtp_details"])
                return (
                    {
                        "is_successful": True,
                        "email": smtp_details["email"],
                        "message": "SMTP Email successfully fetched.",
                    },
                    HTTPStatus.OK,
                )

            return (
                {
                    "is_successful": False,
                    "message": "SMTP Email not found for the given user.",
                },
                HTTPStatus.NOT_FOUND,
            )
        except Exception as e:
            return (
                {
                    "is_successful": False,
                    "message": f"An error occurred while fetching SMTP email: {str(e)}",
                },
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def upsert_image(
        self, current_user_email: str, company_admin_email: str, image_type: str, image_file: Any = None
    ) -> tuple[dict, int]:

        # Validate image type
        validation_result = self._validate_image_type(image_type)
        if not validation_result["is_successful"]:
            return validation_result, HTTPStatus.BAD_REQUEST

        field_name = f"{image_type}_data"

        try:
            image_data = None
            if image_file:
                image_data = self.save_image_to_base64(image_file)

            result = self.collection.update_one(
                {"company_admin_email": company_admin_email},
                {"$set": {field_name: image_data}},
                upsert=True,
            )

            if result.modified_count > 0 or result.upserted_id is not None:
                LogManager.add_log(
                    current_user_email=current_user_email,
                    company_admin_email=company_admin_email,
                    log_action_type=LogActionType.ADD,
                    message=f"ADDED {image_type.capitalize()} to the configuration.",
                )
                return (
                    {
                        "is_successful": True,
                        "message": f"{image_type.capitalize()} successfully updated.",
                    },
                    HTTPStatus.OK,
                )

            return (
                {
                    "is_successful": False,
                    "message": f"Failed to update the {image_type}. Please try again.",
                },
                HTTPStatus.BAD_REQUEST,
            )
        except ValueError as e:
            return (
                {
                    "is_successful": False,
                    "message": str(e),
                },
                HTTPStatus.BAD_REQUEST,
            )
        except Exception as e:
            return (
                {
                    "is_successful": False,
                    "message": f"An error occurred while uploading {image_type}: {str(e)}",
                },
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def get_image_data(self, company_admin_email: str, image_type: str) -> tuple[dict, int]:
        """
        Generic method to fetch image data (logo, signature, or stamp).

        Args:
            company_admin_email (str): Email of the company admin.
            image_type (str): Type of image - must be 'logo', 'signature', or 'stamp'.

        Returns:
            tuple[dict, int]: Success status, message, image data, and HTTP status code.
        """
        # Validate image type
        validation_result = self._validate_image_type(image_type)
        if not validation_result["is_successful"]:
            return validation_result, HTTPStatus.BAD_REQUEST

        field_name = f"{image_type}_data"

        try:
            record = self.collection.find_one({"company_admin_email": company_admin_email}, {"_id": 0, field_name: 1})

            if record and record.get(field_name):
                return (
                    {
                        "is_successful": True,
                        "data": record[field_name],
                        "message": f"{image_type.capitalize()} data successfully fetched.",
                    },
                    HTTPStatus.OK,
                )

            return (
                {
                    "is_successful": False,
                    "message": f"{image_type.capitalize()} hasn't been uploaded yet.",
                },
                HTTPStatus.NOT_FOUND,
            )
        except Exception as e:
            return (
                {
                    "is_successful": False,
                    "message": f"An error occurred while fetching {image_type}: {str(e)}",
                },
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def delete_image(self, current_user_email: str, company_admin_email: str, image_type: str) -> tuple[dict, int]:
        """
        Generic method to delete an image (logo, signature, or stamp).

        Args:
            current_user_email (str): Email of the current user performing the action.
            company_admin_email (str): Email of the company admin.
            image_type (str): Type of image - must be 'logo', 'signature', or 'stamp'.

        Returns:
            tuple[dict, int]: Success status, message, and HTTP status code.
        """
        # Validate image type
        validation_result = self._validate_image_type(image_type)
        if not validation_result["is_successful"]:
            return validation_result, HTTPStatus.BAD_REQUEST

        field_name = f"{image_type}_data"

        try:
            result = self.collection.update_one(
                {"company_admin_email": company_admin_email},
                {"$unset": {field_name: ""}},
            )

            if result.modified_count > 0:
                LogManager.add_log(
                    current_user_email=current_user_email,
                    company_admin_email=company_admin_email,
                    log_action_type=LogActionType.DELETE,
                    message=f"DELETED {image_type.capitalize()} from the configuration.",
                )
                return (
                    {
                        "is_successful": True,
                        "message": f"{image_type.capitalize()} successfully deleted.",
                    },
                    HTTPStatus.OK,
                )

            return (
                {
                    "is_successful": False,
                    "message": f"Failed to delete the {image_type}. It may not exist.",
                },
                HTTPStatus.NOT_FOUND,
            )
        except Exception as e:
            return (
                {
                    "is_successful": False,
                    "message": f"An error occurred while deleting {image_type}: {str(e)}",
                },
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def delete_smtp_details(self, current_user_email: str, company_admin_email: str) -> tuple[dict, int]:
        """
        Delete SMTP configuration details.

        Args:
            current_user_email (str): Email of the current user performing the action.
            company_admin_email (str): Email of the company admin.

        Returns:
            tuple[dict, int]: Success status, message, and HTTP status code.
        """
        try:
            result = self.collection.update_one(
                {"company_admin_email": company_admin_email},
                {"$unset": {"smtp_details": ""}},
            )

            if result.modified_count > 0:
                LogManager.add_log(
                    current_user_email=current_user_email,
                    company_admin_email=company_admin_email,
                    log_action_type=LogActionType.DELETE,
                    message="DELETED SMTP Details from the configuration.",
                )
                return (
                    {
                        "is_successful": True,
                        "message": "SMTP Details successfully deleted.",
                    },
                    HTTPStatus.OK,
                )

            return (
                {
                    "is_successful": False,
                    "message": "Failed to delete SMTP Details. They may not exist.",
                },
                HTTPStatus.NOT_FOUND,
            )
        except Exception as e:
            return (
                {
                    "is_successful": False,
                    "message": f"An error occurred while deleting SMTP details: {str(e)}",
                },
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def save_image_to_base64(self, file: Any) -> str:
        """
        Validates and converts an image file to base64 string.

        Args:
            file (Any): The file object to convert (FastAPI UploadFile).

        Returns:
            str: Base64-encoded image with MIME type prefix.

        Raises:
            ValueError: If file validation fails (size, type, or dimensions).
        """
        if not file:
            raise ValueError("No file provided.")

        if not hasattr(file, "filename") or not file.filename:
            raise ValueError("Invalid file object. Missing filename.")

        file_extension = file.filename.split(".")[-1].lower()
        if file_extension not in ("jpg", "jpeg", "png"):
            raise ValueError("Unsupported file type. Please upload a JPG or PNG image.")

        file.file.seek(0)
        image_bytes = file.file.read()
        file_size = len(image_bytes)

        if file_size > self.MAX_FILE_SIZE:
            raise ValueError("The file exceeds the maximum allowed size of 1 MB.")

        try:
            from io import BytesIO

            with Image.open(BytesIO(image_bytes)) as img:
                width, height = img.size
                if width > self.REQUIRED_DIMENSIONS[0] or height > self.REQUIRED_DIMENSIONS[1]:
                    raise ValueError("The image dimensions must not exceed 500x500 pixels.")
        except Exception as e:
            raise ValueError(f"Invalid image file: {str(e)}")

        base64_string = base64.b64encode(image_bytes).decode("utf-8")

        mime_type = f"image/{file_extension if file_extension != 'jpg' else 'jpeg'}"
        return f"data:{mime_type};base64,{base64_string}"

    def fetch_all_config(self, company_admin_email: str) -> tuple[dict, int]:
        """
        Fetch all configuration data for a company admin.

        Args:
            company_admin_email (str): Email of the company admin.

        Returns:
            tuple[dict, int]: Configuration data including logo, stamp, signature, and HTTP status code.
        """
        try:
            record = self.collection.find_one({"company_admin_email": company_admin_email}, {"_id": 0})

            config = {"is_successful": True, "logo_data": "", "stamp_data": "", "signature_data": ""}

            if not record:
                return config, HTTPStatus.OK

            config.update(
                {
                    "logo_data": record.get("logo_data", ""),
                    "stamp_data": record.get("stamp_data", ""),
                    "signature_data": record.get("signature_data", ""),
                }
            )

            return config, HTTPStatus.OK
        except Exception as e:
            return (
                {
                    "is_successful": False,
                    "message": f"An error occurred while fetching configuration: {str(e)}",
                },
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    @classmethod
    def get_smtp_details(cls, company_admin_email: str) -> tuple[dict, int]:
        """
        Fetch and decrypt SMTP details for a company admin.

        Args:
            company_admin_email (str): Email of the company admin.

        Returns:
            tuple[dict, int]: SMTP details including email, password, provider, and HTTP status code.
        """
        try:
            document = cls.collection.find_one(
                {"company_admin_email": company_admin_email}, {"smtp_details": 1, "_id": 0}
            )

            if document and "smtp_details" in document:
                encrytion_system = EncryptionSystem()
                smtp_details = encrytion_system.decrypt_string(encrypted_string=document["smtp_details"])
                return (
                    {
                        "is_successful": True,
                        "email": smtp_details["email"],
                        "password": smtp_details["password"],
                        "provider": smtp_details["provider"],
                        "message": "SMTP Details successfully fetched.",
                    },
                    HTTPStatus.OK,
                )
            return (
                {
                    "is_successful": False,
                    "message": "SMTP Details are not configured.",
                },
                HTTPStatus.NOT_FOUND,
            )
        except Exception as e:
            return (
                {
                    "is_successful": False,
                    "message": f"An error occurred while fetching SMTP details: {str(e)}",
                },
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
