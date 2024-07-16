from pydantic import BaseModel


class ProcessProjectTagRequest(BaseModel):
    project_path: str
    project_tag: str
