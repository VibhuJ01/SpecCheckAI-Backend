import threading
from datetime import datetime, timedelta, timezone
from email.mime.image import MIMEImage
from typing import Any

from src.cred import Credentials
from src.encryption_system import EncryptionSystem
from src.enums import MongoCollectionsNames, UserRoles
from src.mongodb.authentication_system import AuthenticationSystem
from src.mongodb.base import BaseDatabase
from src.schema import UserLoginRequest
from src.send_email import SendEmail
from src.utils import generate_randomised_numeric_string, one_way_hashing


class AuthorisationSystem:
    collection = BaseDatabase.get_collection(collection_name=MongoCollectionsNames.USER_MASTER)
    company_collection = BaseDatabase.get_collection(collection_name=MongoCollectionsNames.COMPANY_MASTER)

    def user_login(self, login_data: dict) -> dict:
        """Authorises user data during login
        Args:
            login data (dict): User's login data
        Returns:
            dict: successful or not - user exists or not
            {"is_successful": True | False, "is_user_exists": True | False}
        """

        login_request = UserLoginRequest.model_validate(login_data)
        email_lower = login_request.email.lower()
        user_db = self.collection.find_one({"email": email_lower, "is_disabled": False})
        if not user_db:
            return {
                "is_successful": False,
                "is_user_exists": False,
                "message": f"Email ID: {login_request.email} is not permitted on the portal.",
            }

        # Check if the user is locked out
        if user_db.get("lockout_time"):
            lockout_time = user_db["lockout_time"]
            if lockout_time.tzinfo is None:
                lockout_time = lockout_time.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) < lockout_time:
                remaining_time = lockout_time - datetime.now(timezone.utc)
                hours, remainder = divmod(remaining_time.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                return {
                    "is_successful": False,
                    "is_user_exists": True,
                    "message": f"Account is locked. Try again later. Lockout ends in {hours} hours, {minutes} minutes, and {seconds} seconds.",
                }

        login_request.password = one_way_hashing(login_request.password)
        user_db_pass = user_db.get("password")

        if user_db_pass != login_request.password:
            # Increment login attempts
            login_attempts = user_db.get("login_attempts", 0) + 1
            lockout_time = None

            # Set lockout time if necessary
            MAX_LOGIN_ATTEMPTS_PER_DAY = 20
            LOCKOUT_COUNTER = 5
            if login_attempts >= MAX_LOGIN_ATTEMPTS_PER_DAY:
                lockout_time = datetime.now(timezone.utc) + timedelta(days=1)
                login_attempts = 0  # Set login attempts as 0 after final penality

            elif login_attempts % LOCKOUT_COUNTER == 0:
                lockout_time = datetime.now(timezone.utc) + timedelta(minutes=5 * (login_attempts // LOCKOUT_COUNTER))

            self.collection.update_one(
                {"email": email_lower},
                {"$set": {"login_attempts": login_attempts, "lockout_time": lockout_time}},
            )

            return {"is_successful": False, "is_user_exists": True, "message": f"Email ID and Password doesn't match."}

        # Reset login attempts, update lockout time, refresh token, and JWT secret in a single query
        login_request.refresh_token_info = AuthenticationSystem.generate_refresh_token()
        self.collection.update_one(
            {"email": email_lower},
            {
                "$set": {
                    "login_attempts": 0,
                    "lockout_time": None,
                    "refresh_token": login_request.refresh_token_info["refresh_token"],
                    "token_validity": login_request.refresh_token_info["token_validity"],
                    "jwt_secret": AuthenticationSystem.generate_refresh_token()["refresh_token"],
                }
            },
        )

        authentication_system = AuthenticationSystem()
        get_access_token_data = {
            "email": login_request.email,
            "refresh_token": login_request.refresh_token_info["refresh_token"],
        }
        jwt_token_info = authentication_system.generate_access_token(get_access_token_data=get_access_token_data)

        encryption_system = EncryptionSystem()
        encryption_dict = {
            "email": login_request.email.lower(),
            "refresh_token": login_request.refresh_token_info["refresh_token"],
            "jwt_token": jwt_token_info["jwt_token"],
            "role": user_db["role"],
        }

        if user_db["role"] == UserRoles.COMPANY_ADMIN:
            encryption_dict["company_admin_email"] = user_db["email"]
        elif user_db["role"] == UserRoles.EMPLOYEE:
            encryption_dict["company_admin_email"] = user_db["company_admin_email"]

        # is_lead_management_enabled = False
        # is_lucky_draw_enabled = False
        # if user_db["role"] in [UserRoles.COMPANY_ADMIN, UserRoles.EMPLOYEE]:
        #     company_data = self.company_collection.find_one({"email": encryption_dict["company_admin_email"]})
        #     if company_data:
        #         is_lead_management_enabled = company_data.get("is_lead_management_enabled", False)
        #         is_lucky_draw_enabled = company_data.get("is_lucky_draw_enabled", False)

        auth_token = encryption_system.encrypt_dict(input_json=encryption_dict)
        return {
            "is_successful": True,
            "is_user_exists": True,
            "auth_token": auth_token,
            "message": "Sign-in successful!",
            "name": user_db["name"],
            "role": user_db["role"],
            "permissions": user_db.get("permissions", {}),
            "email": email_lower,
        }

    def user_logout_db(self, email: str) -> dict:
        """Logs user out
        Args:
            email (dict): User's email id
        Returns:
            dict: successful or not - user exists or not
            {"is_successful": True | False, "is_user_exists": True | False}
        """
        email_lower = email.lower()
        user = self.collection.find_one({"email": email_lower})

        if not user:
            return {"is_successful": False, "is_user_exists": False, "message": "User does not exist."}

        self.collection.update_one(
            {"email": email_lower},
            {"$unset": {"refresh_token": "", "token_validity": "", "jwt_secret": ""}},
        )

        return {"is_successful": True, "is_user_exists": True, "message": "User logged out successfully."}

    def is_email_exists(self, email: str) -> bool:
        user_exists = self.collection.find_one({"email": email, "is_disabled": False})
        return user_exists is not None

    def send_reset_password_otp(self, email: str) -> dict[str, Any]:
        email_lower = email.lower()
        user = self.collection.find_one({"email": email_lower, "is_disabled": False})
        if not user:
            return {
                "is_successful": False,
                "message": f"Either Email '{email_lower}' does not exist or is not permitted on the portal.",
            }

        # Check the last OTP request time
        last_otp_time = user.get("last_otp_time")
        if last_otp_time:
            # Convert last_otp_time to timezone-aware if it's not
            if last_otp_time.tzinfo is None:
                last_otp_time = last_otp_time.replace(tzinfo=timezone.utc)

            time_since_last_otp = datetime.now(timezone.utc) - last_otp_time
            if time_since_last_otp < timedelta(seconds=30):
                return {
                    "is_successful": False,
                    "message": "You can only request a new OTP every 30 seconds.",
                }

        send_email = SendEmail()
        otp = generate_randomised_numeric_string(length=6)
        is_successful = send_email.send_forgot_password_otp_email(receiver_email=email_lower, otp=otp)

        if not is_successful:
            return {
                "is_successful": False,
                "message": "Error sending OTP in email. Please check your email and try again",
            }

        self.collection.update_one(
            {"email": email_lower}, {"$set": {"reset_password_otp": otp, "last_otp_time": datetime.now(timezone.utc)}}
        )

        OTP_VALIDITY = 10  # In minutes
        timer = threading.Timer(OTP_VALIDITY * 60, self.delete_reset_password_otp, [email_lower])
        timer.start()

        return {
            "is_successful": True,
            "message": "OTP has been sent to your email and it will be valid for 5 minutes only.",
        }

    def delete_reset_password_otp(self, email: str) -> None:
        """Deletes the reset_password_otp attribute from the database."""
        self.collection.update_one({"email": email}, {"$unset": {"reset_password_otp": "", "last_otp_time": ""}})

    def delete_update_password_permission(self, email: str) -> None:
        """Deletes the update_password_permission attribute from the database."""
        self.collection.update_one({"email": email}, {"$unset": {"update_password_permission": ""}})

    def verify_reset_password_otp(self, email: str, input_otp: str) -> dict[str, Any]:

        email_lower = email.lower()
        user = self.collection.find_one({"email": email_lower, "is_disabled": False})
        if not user:
            return {
                "is_successful": False,
                "message": f"Either Email '{email_lower}' does not exist or is not permitted on the portal.",
            }

        # Get the current number of attempts
        otp_attempts = user.get("otp_attempts", 0)
        MAX_OTP_ATTEMPTS = 5

        if otp_attempts >= MAX_OTP_ATTEMPTS:
            self.collection.update_one(
                {"email": email_lower}, {"$unset": {"reset_password_otp": ""}, "$set": {"otp_attempts": 0}}
            )
            return {"is_successful": False, "message": "Maximum OTP attempts reached. Please request a new OTP."}

        if user.get("reset_password_otp") == input_otp:
            PASSWORD_RESET_VALIDITY = 5  # In minutes
            self.collection.update_one(
                {"email": email_lower},
                {
                    "$set": {"otp_attempts": 0, "update_password_permission": True},
                    "$unset": {"reset_password_otp": "", "last_otp_time": ""},
                },
            )
            timer = threading.Timer(PASSWORD_RESET_VALIDITY * 60, self.delete_update_password_permission, [email_lower])
            timer.start()

            return {"is_successful": True, "message": "OTP verified successfully!"}
        else:
            otp_attempts += 1
            self.collection.update_one({"email": email_lower}, {"$set": {"otp_attempts": otp_attempts}})
            attempts_left = MAX_OTP_ATTEMPTS - otp_attempts
            return {
                "is_successful": False,
                "message": f"Invalid OTP, please try again! You have {attempts_left} attempts left.",
            }

    def update_password(self, email: str, new_password: str) -> dict[str, Any]:

        email_lower = email.lower()
        user = self.collection.find_one({"email": email_lower, "is_disabled": False})
        if not user.get("update_password_permission", False):  # type: ignore
            return {"is_successful": False, "message": "You do not have permission to update the password"}

        hashed_password = one_way_hashing(new_password)
        self.collection.update_one(
            {"email": email_lower},
            {
                "$set": {"password": hashed_password},
                "$unset": {
                    "lockout_time": "",
                    "login_attempts": 0,
                    "update_password_permission": False,
                    "reset_password_otp": "",
                    "last_otp_time": "",
                },
            },
        )

        return {"is_successful": True, "message": "Password updated successfully!"}

    def change_password(self, email: str, old_password: str, new_password: str) -> dict:
        """Updates user password if old password matches and new password is valid.

        Args:
            email (str): User's email address
            old_password (str): User's current password
            new_password (str): User's desired new password

        Returns:
            dict: {"is_successful": True/False, "message": str}
                - is_successful: True if password updated successfully, False otherwise
                - message: Descriptive message indicating the result
        """
        email_lower = email.lower()
        user_db = self.collection.find_one({"email": email_lower, "is_disabled": False})

        if not user_db:
            return {"is_successful": False, "message": "User not found or account is disabled."}

        if user_db.get("password") != one_way_hashing(old_password):
            return {"is_successful": False, "message": "Old password is incorrect."}

        hashed_new_password = one_way_hashing(new_password)
        self.collection.update_one({"email": email_lower}, {"$set": {"password": hashed_new_password}})

        return {"is_successful": True, "message": "Password updated successfully."}
