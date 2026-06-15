from pydantic import BaseModel, ConfigDict


class APISchema(BaseModel):
    """Base for all API Schemas"""

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
    )
