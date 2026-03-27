from datetime import datetime

import pytz

from src.enums import LogActionType, MongoCollectionsNames
from src.mongodb.base import BaseDatabase
from src.utils import fetch_profile


class LogManager:
    collection = BaseDatabase.get_collection(collection_name=MongoCollectionsNames.LOG_MANAGER)

    @classmethod
    def add_log(
        cls,
        current_user_email: str,
        company_admin_email: str,
        log_action_type: LogActionType,
        message: str,
    ) -> dict:

        ist_timezone = pytz.timezone("Asia/Kolkata")
        current_ist_time = datetime.now(ist_timezone)
        formatted_date = current_ist_time.strftime("%d-%m-%Y")
        formatted_time = current_ist_time.strftime("%I:%M:%S %p IST")

        if current_user_email == "Event Attendee: QR Code Scan":
            message = f"{message} using QR code scan"
            user_data = {
                "name": "Event Attendee",
                "email": "N/A",
            }

        else:
            user_data = fetch_profile(email=current_user_email)
            message = f"{user_data['name']}({user_data['email']}) {message}"

        log = {
            "time": formatted_time,
            "date": formatted_date,
            "action_performer_name": user_data["name"],
            "action_performer_email": user_data["email"],
            "message": message,
            "action_type": log_action_type.value,
            "company_admin_email": company_admin_email,
            "timestamp": current_ist_time,
        }

        # Perform the upsert operation
        result = cls.collection.insert_one(log)

        # Check the operation result
        if result.inserted_id is not None:
            return {"is_successful": True, "message": "Log successfully added."}

        return {"is_successful": False, "message": "Failed to add the log. Please try again."}

    @classmethod
    def fetch_logs(cls, company_admin_email: str, page_number: int) -> dict:
        BATCH_SIZE = 50
        skip = BATCH_SIZE * (page_number - 1)

        query = {"company_admin_email": company_admin_email}

        total_logs = cls.collection.count_documents(query)
        total_pages = (total_logs + BATCH_SIZE - 1) // BATCH_SIZE

        cursor = (
            cls.collection.find(query, {"_id": 0, "company_admin_email": 0, "timestamp": 0})
            .sort("timestamp", -1)
            .skip(skip)
            .limit(BATCH_SIZE)
        )

        logs = list(cursor)

        return {
            "activity_logs": logs,
            "is_successful": True,
            "total_pages": total_pages,
        }

    @classmethod
    def search_logs(
        cls,
        company_admin_email: str,
        search_query: str,
        page_number: int,
    ) -> dict:
        BATCH_SIZE = 50
        skip = BATCH_SIZE * (page_number - 1)

        search_query = search_query.strip()

        query = {
            "company_admin_email": company_admin_email,
            "$or": [
                {"date": {"$regex": search_query, "$options": "i"}},
                {"action_performer_name": {"$regex": search_query, "$options": "i"}},
                {"action_performer_email": {"$regex": search_query, "$options": "i"}},
                {"action_type": {"$regex": search_query, "$options": "i"}},
                {"message": {"$regex": search_query, "$options": "i"}},
            ],
        }

        total_logs = cls.collection.count_documents(query)
        total_pages = (total_logs + BATCH_SIZE - 1) // BATCH_SIZE

        cursor = (
            cls.collection.find(query, {"_id": 0, "company_admin_email": 0})
            .sort("timestamp", -1)
            .skip(skip)
            .limit(BATCH_SIZE)
        )

        logs = list(cursor)

        return {
            "activity_logs": logs,
            "is_successful": True,
            "total_pages": total_pages,
        }
