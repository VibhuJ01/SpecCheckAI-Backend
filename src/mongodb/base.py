from pymongo import ASCENDING, MongoClient, collection

from src.cred import Credentials
from src.enums import MongoCollectionsNames


class BaseDatabase:
    mongo_client = MongoClient(Credentials.mongo_url)
    db = mongo_client[Credentials.db_name]

    @classmethod
    def get_collection(cls, collection_name) -> collection.Collection:
        return cls.db[collection_name]

    @classmethod
    def ensure_indexes(cls):
        """Drop existing indexes and create fresh ones for all collections."""

        # USER_MASTER Collection Indexes
        user_master_collection = cls.get_collection(MongoCollectionsNames.USER_MASTER)
        user_master_collection.drop_indexes()

        user_master_collection.create_index([("email", ASCENDING)], name="email_idx", unique=True)
        user_master_collection.create_index([("company_admin_email", ASCENDING)], name="company_admin_idx")
        user_master_collection.create_index(
            [("email", ASCENDING), ("company_admin_email", ASCENDING)], name="email_company_idx"
        )

        # COMPANY_MASTER Collection Indexes
        company_master_collection = cls.get_collection(MongoCollectionsNames.COMPANY_MASTER)
        company_master_collection.drop_indexes()

        company_master_collection.create_index([("email", ASCENDING)], name="email_idx")

        # LOG_MANAGER Collection Indexes
        log_manager_collection = cls.get_collection(MongoCollectionsNames.LOG_MANAGER)
        log_manager_collection.drop_indexes()

        log_manager_collection.create_index([("company_admin_email", ASCENDING)], name="company_admin_idx")
        log_manager_collection.create_index([("created_at", ASCENDING)], name="created_at_idx")
