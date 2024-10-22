# app/utils/object_id.py
from bson import ObjectId
from pydantic import GetJsonSchemaHandler
from typing import Any

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetJsonSchemaHandler
    ) -> Any:
        return {
            "type": "string",
            "description": "ObjectId string representation",
            "examples": ["507f1f77bcf86cd799439011"]
        }