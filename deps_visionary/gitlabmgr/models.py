from typing import List, Dict, Generator
from pydantic import BaseModel, RootModel


class ProjectSearchModel(BaseModel):
    id: int
    name: str
    default_branch: str
    path_with_namespace: str


class ProjectSearchModelList(RootModel):
    root: List[ProjectSearchModel]

    def __iter__(self) -> Generator[ProjectSearchModel, None, None]:
        yield from self.root


class ProjectsCacheModel(RootModel):
    root: Dict[str, ProjectSearchModel]  # key: path_with_namespace


class Commit(BaseModel):
    id: str
    created_at: str
    title: str


class ProjectTag(BaseModel):
    name: str
    commit: Commit


class ProjectTagList(RootModel):
    root: List[ProjectTag]

    def __iter__(self) -> Generator[ProjectTag, None, None]:
        yield from self.root


class ProjectFile(BaseModel):
    id: str
    name: str
    path: str
    mode: str


class ProjectFileList(RootModel):
    root: List[ProjectFile]

    def __iter__(self) -> Generator[ProjectFile, None, None]:
        yield from self.root
