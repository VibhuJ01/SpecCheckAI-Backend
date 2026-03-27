import datetime
import secrets
from typing import Any

import jwt

from src.constants import MAX_AUTH_DAYS
from src.enums import AuthTokenType, MongoCollectionsNames
from src.mongodb.base import BaseDatabase
from src.schema import GetAccessTokenRequest


class AuthenticationSystem:
    def generate_access_token(self, get_access_token_data: dict) -> dict[str, Any]:
        """It generates and returns access token

        Args:
            user_details (dict): user's details

        Returns:
            str: JWT token
        """

        get_access_token_request = GetAccessTokenRequest.model_validate(get_access_token_data)
        payload = {
            "email": get_access_token_request.email,
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=MAX_AUTH_DAYS),
        }

        token = jwt.encode(
            payload, self.get_user_token_info(email=get_access_token_request.email)["jwt_secret"], algorithm="HS256"
        )

        return {
            "is_successful": True,
            "jwt_token": token,
            "is_expired": False,
            "message": "Access token generated successfully.",
        }

    @staticmethod
    def generate_refresh_token() -> dict:
        """Generates and returns refresh token and its validity

        Returns:
            dict: refresh token and its validity
        """
        refresh_token = secrets.token_urlsafe(32)
        validity_time = (
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=MAX_AUTH_DAYS)
        ).isoformat()
        return {"refresh_token": refresh_token, "token_validity": validity_time}

    def check_tokens_validity(self, email: str, jwt_token: str, refresh_token: str) -> dict:
        """It validates JWT token

        Args:
            token (str): jwt_token

        Returns:
            dict: {"is_valid": True | False, "is_token_valid": True | False}
        """

        user_info = self.get_user_token_info(email=email)

        if not user_info["is_successful"]:
            return user_info

        if refresh_token != user_info["refresh_token"]:
            return {
                "is_successful": False,
                "token_type": AuthTokenType.REFRESH_TOKEN,
                "message": "Refresh token is not valid",
            }

        validity_time = datetime.datetime.fromisoformat(user_info["token_validity"])
        current_time = datetime.datetime.now(datetime.timezone.utc)

        if current_time > validity_time:
            return {
                "is_successful": False,
                "token_type": AuthTokenType.REFRESH_TOKEN,
                "is_expired": True,
                "message": "Refresh token has expired.",
            }

        # ----------------------------------------------------------------------------------------

        try:

            jwt.decode(jwt_token, user_info["jwt_secret"], algorithms=["HS256"])

            return {
                "is_successful": True,
                "is_expired": False,
                "message": "JWT token is valid",
            }

        except jwt.ExpiredSignatureError:
            return {
                "token_type": AuthTokenType.JWT_TOKEN,
                "is_expired": True,
                "is_successful": False,
                "message": "JWT token has expired.",
            }

        except jwt.InvalidTokenError:
            return {
                "token_type": AuthTokenType.JWT_TOKEN,
                "is_successful": False,
                "is_expired": None,
                "message": "Token is Invalid. Please contact support!!",
            }

    def get_user_token_info(self, email: str) -> dict:
        """Retrieve user's refresh token from database
        Args:
            email (str): user's email
        Returns:
            dict: refresh token info
        """

        collection = BaseDatabase.get_collection(collection_name=MongoCollectionsNames.USER_MASTER)
        user_db_data = collection.find_one({"email": email.lower(), "is_disabled": False})

        if not user_db_data:
            return {"is_successful": False, "message": "user doesn't exist"}

        refresh_token = user_db_data.get("refresh_token")

        if not refresh_token:
            return {"is_successful": False, "message": "Refresh token not found."}

        return {
            "is_successful": True,
            "refresh_token": refresh_token,
            "token_validity": user_db_data.get("token_validity"),
            "jwt_secret": user_db_data.get("jwt_secret"),
        }
