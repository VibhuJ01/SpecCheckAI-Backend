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

        # GENERAL_CONFIG Collection Indexes
        general_config_collection = cls.get_collection(MongoCollectionsNames.GENERAL_CONFIG)
        general_config_collection.drop_indexes()

        general_config_collection.create_index(
            [("company_admin_email", ASCENDING)], name="company_admin_idx", unique=True
        )

        # DEPARTMENT_MASTER Collection Indexes
        department_master_collection = cls.get_collection(MongoCollectionsNames.DEPARTMENT_MASTER)
        department_master_collection.drop_indexes()

        department_master_collection.create_index([("company_admin_email", ASCENDING)], name="company_admin_idx")
        department_master_collection.create_index(
            [("department_code", ASCENDING), ("company_admin_email", ASCENDING)],
            name="department_code_company_idx",
        )

        # TEAM_MASTER Collection Indexes
        team_master_collection = cls.get_collection(MongoCollectionsNames.TEAM_MASTER)
        team_master_collection.drop_indexes()

        team_master_collection.create_index([("company_admin_email", ASCENDING)], name="company_admin_idx")
        team_master_collection.create_index(
            [("team_code", ASCENDING), ("company_admin_email", ASCENDING)],
            name="team_code_company_idx",
        )
        team_master_collection.create_index(
            [("team_name", ASCENDING), ("company_admin_email", ASCENDING)],
            name="team_name_company_idx",
        )

        # CLIENT_MASTER Collection Indexes
        client_master_collection = cls.get_collection(MongoCollectionsNames.CLIENT_MASTER)
        client_master_collection.drop_indexes()

        client_master_collection.create_index([("company_admin_email", ASCENDING)], name="company_admin_idx")
        client_master_collection.create_index(
            [("email", ASCENDING), ("company_admin_email", ASCENDING)],
            name="email_company_idx",
            unique=True,
        )

        # SPECIFICATION_MATRIX Collection Indexes
        specification_matrix_collection = cls.get_collection(MongoCollectionsNames.SPECIFICATION_MATRIX)
        specification_matrix_collection.drop_indexes()

        specification_matrix_collection.create_index([("company_admin_email", ASCENDING)], name="company_admin_idx")
        specification_matrix_collection.create_index(
            [("code", ASCENDING), ("company_admin_email", ASCENDING)],
            name="code_company_idx",
        )

        # STANDARD_MASTER Collection Indexes
        standard_master_collection = cls.get_collection(MongoCollectionsNames.STANDARD_MASTER)
        standard_master_collection.drop_indexes()

        standard_master_collection.create_index([("company_admin_email", ASCENDING)], name="company_admin_idx")
        standard_master_collection.create_index([("standard_code", ASCENDING)], name="standard_code_idx", unique=True)
        standard_master_collection.create_index(
            [("standard_code", ASCENDING), ("company_admin_email", ASCENDING)],
            name="standard_code_company_idx",
        )
        standard_master_collection.create_index(
            [("specification_code", ASCENDING), ("company_admin_email", ASCENDING)],
            name="specification_code_company_idx",
        )

        # EMPLOYEE_SIGNATURES Collection Indexes
        employee_signatures_collection = cls.get_collection(MongoCollectionsNames.EMPLOYEE_SIGNATURES)
        employee_signatures_collection.drop_indexes()

        employee_signatures_collection.create_index(
            [("employee_email", ASCENDING), ("company_admin_email", ASCENDING)],
            name="employee_email_company_idx",
            unique=True,
        )
