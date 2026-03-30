from typing import Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from src.enums import EmployeePermissionType


class UserLoginRequest(BaseModel):
    email: str
    password: str
    refresh_token_info: Optional[dict] = None


class AddUpdateUserRequest(BaseModel):
    email: str
    name: str
    phone_number: int


class GetAccessTokenRequest(BaseModel):
    email: str
    refresh_token: str


# Company Master
class CompanyDetails(BaseModel):
    legal_name: str = Field(..., max_length=100)
    phone_number: str = Field(..., max_length=20)
    address_1: str = Field(..., max_length=100)
    address_2: Optional[str] = Field(None, max_length=100)
    country: str = Field(..., max_length=50)
    state: str = Field(..., max_length=50)
    city: str = Field(..., max_length=50)
    pincode: str = Field(..., max_length=10)

    # Contact Info
    name: str = Field(..., max_length=100)
    email: str = Field(..., max_length=300)
    mobile_number: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=100)
    designation: Optional[str] = Field(None, max_length=100)

    # Limits
    reporting_code: str = Field(..., max_length=10)
    employee_access_limit: int
    is_ai_file_upload_enabled: bool = False
    is_ai_voice_assistant_enabled: bool = False
    is_back_date_booking_enabled: bool = False

    # Tax Info
    assessee_code: Optional[str] = Field(None, max_length=40)
    pan_no: Optional[str] = Field(None, max_length=10)
    tcs_applicable: Optional[bool]
    gst_no: Optional[str] = Field(None, max_length=15)
    gst_customer_type: Optional[str] = Field(None, max_length=30)
    gst_reg_type: Optional[str] = Field(None, max_length=10)

    # Bank Info
    bank_name: Optional[str] = Field(None, max_length=100)
    account_number: Optional[str] = Field(None, max_length=30)
    branch_code: Optional[str] = Field(None, max_length=20)
    ifsc_code: Optional[str] = Field(None, max_length=30)


# Employee Master
class EmployeePermissions(BaseModel):
    general_configuration: EmployeePermissionType = EmployeePermissionType.NOT_ALLOWED

    department_master: EmployeePermissionType = EmployeePermissionType.NOT_ALLOWED
    team_master: EmployeePermissionType = EmployeePermissionType.NOT_ALLOWED
    employee_master: EmployeePermissionType = EmployeePermissionType.NOT_ALLOWED
    client_master: EmployeePermissionType = EmployeePermissionType.NOT_ALLOWED
    specification_matrix: EmployeePermissionType = EmployeePermissionType.NOT_ALLOWED

    sample_collection: EmployeePermissionType = EmployeePermissionType.NOT_ALLOWED
    sample_management: EmployeePermissionType = EmployeePermissionType.NOT_ALLOWED
    sample_testing: EmployeePermissionType = EmployeePermissionType.NOT_ALLOWED
    sample_review: EmployeePermissionType = EmployeePermissionType.NOT_ALLOWED
    sample_approval: EmployeePermissionType = EmployeePermissionType.NOT_ALLOWED

    sample_closed: EmployeePermissionType = EmployeePermissionType.NOT_ALLOWED
    sample_tracking: EmployeePermissionType = EmployeePermissionType.NOT_ALLOWED
    activity_logs: EmployeePermissionType = EmployeePermissionType.NOT_ALLOWED


class EmployeeDetails(BaseModel):
    name: str = Field(..., max_length=80)
    email: str = Field(..., max_length=80)
    phone_number: str = Field(..., max_length=30)
    permissions: EmployeePermissions


# Team Master
class TeamDetails(BaseModel):
    team_name: str = Field(..., max_length=50)
    team_description: str = Field(..., max_length=100)


# Client Master
class ClientDetails(BaseModel):
    legal_name: str = Field(..., max_length=100)
    phone_number: str = Field(..., max_length=20)
    address_1: str = Field(..., max_length=100)
    address_2: Optional[str] = Field(None, max_length=100)
    country: str = Field(..., max_length=50)
    state: str = Field(..., max_length=50)
    city: str = Field(..., max_length=50)
    pincode: str = Field(..., max_length=10)

    # Contact Info
    name: str = Field(..., max_length=100)
    email: str = Field(..., max_length=300)
    mobile_number: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=100)
    designation: Optional[str] = Field(None, max_length=100)

    # Tax Info
    assessee_code: Optional[str] = Field(None, max_length=40)
    pan_no: Optional[str] = Field(None, max_length=10)
    tcs_applicable: Optional[bool]
    gst_no: Optional[str] = Field(None, max_length=15)
    gst_customer_type: Optional[str] = Field(None, max_length=30)
    gst_reg_type: Optional[str] = Field(None, max_length=10)

    # Bank Info
    bank_name: Optional[str] = Field(None, max_length=100)
    account_number: Optional[str] = Field(None, max_length=30)
    branch_code: Optional[str] = Field(None, max_length=20)
    ifsc_code: Optional[str] = Field(None, max_length=30)


# AI Card Analyser
class Examples(BaseModel):
    user_prompt: Union[str, list]
    completion: dict


class JSONSchema(BaseModel):
    role: str
    description: list[str]
    instructions: str
    examples: Optional[list[Examples]] = []
    important_notes: Optional[list] = []
