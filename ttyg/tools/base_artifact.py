from pydantic import BaseModel


class BaseArtifact(BaseModel):
    type: str
