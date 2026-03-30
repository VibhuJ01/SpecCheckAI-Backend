import logging as logger
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any

from pydantic import ValidationError

from src.enums import LogActionType, MongoCollectionsNames
from src.mongodb.base import BaseDatabase
from src.mongodb.log_manager import LogManager
from src.schema import TeamDetails


class TeamMaster:

    collection = BaseDatabase.get_collection(collection_name=MongoCollectionsNames.TEAM_MASTER)

    def add_team(
        self, request_data: dict, current_user_email: str, company_admin_email: str
    ) -> tuple[dict[str, Any], int]:
        """Add a new team record to the database."""

        try:
            validated_data = TeamDetails.model_validate(request_data)
        except ValidationError as e:
            logger.exception("Validation error while adding team", e)
            return {"is_successful": False, "message": "Invalid or incomplete request data."}, HTTPStatus.BAD_REQUEST

        team_code = str(uuid.uuid4())
        team_data = validated_data.model_dump()

        team_data.update(
            {
                "team_code": team_code,
                "company_admin_email": company_admin_email,
                "created_at": datetime.now(timezone.utc),
                "created_by": current_user_email,
            }
        )

        result = self.collection.insert_one(team_data)
        if not result.acknowledged:
            return {
                "is_successful": False,
                "message": "Failed to add team to the database. Please try again.",
            }, HTTPStatus.INTERNAL_SERVER_ERROR

        LogManager.add_log(
            current_user_email=current_user_email,
            company_admin_email=company_admin_email,
            log_action_type=LogActionType.ADD,
            message=f"ADDED team: {validated_data.team_name}",
        )

        return {
            "is_successful": True,
            "message": f"Team '{validated_data.team_name}' added successfully.",
        }, HTTPStatus.OK

    def update_team(
        self, request_data: dict, current_user_email: str, company_admin_email: str
    ) -> tuple[dict[str, Any], int]:
        """Update existing team details."""

        try:
            validated_data = TeamDetails.model_validate(request_data)
        except ValidationError as e:
            logger.exception("Validation error while updating team", e)
            return {"is_successful": False, "message": "Invalid or incomplete request data."}, HTTPStatus.BAD_REQUEST

        team_code = request_data["team_code"]
        existing_team = self.collection.find_one({"team_code": team_code, "company_admin_email": company_admin_email})
        if not existing_team:
            return {
                "is_successful": False,
                "message": f"Team with code '{team_code}' not found.",
            }, HTTPStatus.NOT_FOUND

        updated_data = validated_data.model_dump()
        updated_data.pop("team_code", None)

        updated_data.update(
            {
                "updated_at": datetime.now(timezone.utc),
                "updated_by": current_user_email,
            }
        )

        result = self.collection.update_one(
            {"team_code": team_code, "company_admin_email": company_admin_email},
            {"$set": updated_data},
        )

        if result.matched_count == 0:
            return {
                "is_successful": False,
                "message": "Failed to find the team to update.",
            }, HTTPStatus.NOT_FOUND

        if result.modified_count == 0:
            return {
                "is_successful": True,
                "message": "No changes were made to the team details.",
            }, HTTPStatus.OK

        LogManager.add_log(
            current_user_email=current_user_email,
            company_admin_email=company_admin_email,
            log_action_type=LogActionType.EDIT,
            message=f"UPDATED team: {validated_data.team_name}",
        )

        return {
            "is_successful": True,
            "message": f"Team '{validated_data.team_name}' updated successfully.",
        }, HTTPStatus.OK

    def fetch_all_teams(self, company_admin_email: str) -> tuple[dict[str, Any], int]:
        """Fetch all teams for a specific company admin."""

        teams = list(
            self.collection.find(
                {"company_admin_email": company_admin_email},
                {"_id": 0, "team_code": 1, "team_name": 1, "team_description": 1},
            )
        )

        return {
            "is_successful": True,
            "teams": teams,
        }, HTTPStatus.OK

    def delete_team(
        self, team_code: str, current_user_email: str, company_admin_email: str
    ) -> tuple[dict[str, Any], int]:
        """Delete a team record."""

        existing_team = self.collection.find_one({"team_code": team_code, "company_admin_email": company_admin_email})
        if not existing_team:
            return {
                "is_successful": False,
                "message": f"Team with code '{team_code}' not found.",
            }, HTTPStatus.NOT_FOUND

        result = self.collection.delete_one({"team_code": team_code, "company_admin_email": company_admin_email})

        if result.deleted_count == 0:
            return {
                "is_successful": False,
                "message": f"Failed to delete team with code '{team_code}'.",
            }, HTTPStatus.INTERNAL_SERVER_ERROR

        LogManager.add_log(
            current_user_email=current_user_email,
            company_admin_email=company_admin_email,
            log_action_type=LogActionType.DELETE,
            message=f"DELETED team: {existing_team['team_name']} ({team_code})",
        )

        return {
            "is_successful": True,
            "message": "Team deleted successfully.",
        }, HTTPStatus.OK
