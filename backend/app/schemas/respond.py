from pydantic import BaseModel


class RespondRequest(BaseModel):
    ip: str
    window: str = "5m"