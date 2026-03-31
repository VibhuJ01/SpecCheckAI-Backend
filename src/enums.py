from enum import Enum


class ApiReponseStatus(str, Enum):
    FAILED = "failed"
    PROCESSING = "processing"
    SUCCESS = "success"


class AuthTokenType(str, Enum):
    JWT_TOKEN = "jwt"
    REFRESH_TOKEN = "refresh"


class MongoCollectionsNames(str, Enum):
    USER_MASTER = "user_master"
    COMPANY_MASTER = "company_master"
    GENERAL_CONFIG = "general_config"
    DEPARTMENT_MASTER = "department_master"
    TEAM_MASTER = "team_master"
    CLIENT_MASTER = "client_master"
    LOG_MANAGER = "log_manager"

    # Just for Permissions
    EMPLOYEE_MASTER = "employee_master"


class UserRoles(str, Enum):
    SUPER_ADMIN = "super_admin"
    COMPANY_ADMIN = "company_admin"
    EMPLOYEE = "employee"


class Environments(str, Enum):
    LOCAL = "LOCAL"
    UAT = "UAT"
    PRODUCTION = "PRODUCTION"


class EmployeePermissionType(str, Enum):
    VIEW = "view"
    EDIT = "edit"
    NOT_ALLOWED = "not_allowed"


class GPTModels(str, Enum):
    GPT_5_MINI = "gpt-5-mini"
    GPT_4_1_MINI = "gpt-4.1-mini"


class LogActionType(str, Enum):
    ADD = "add"
    EDIT = "edit"
    DELETE = "delete"
    DISABLE = "disable"
    ENABLE = "enable"
    UPLOADED = "uploaded"
