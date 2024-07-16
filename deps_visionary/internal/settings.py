from functools import lru_cache
from typing import List, Dict
from pydantic import BaseModel
import yaml


SUPPORTED_FILES = (
    "Dockerfile",
    "docker-compose.yaml",
    "conanfile.txt",
    "conanfile.py",
    "requirements.txt",
)


class RedisSettings(BaseModel):
    url: str
    lock_max_time: int


class GitlabSettings(BaseModel):
    url: str
    token: str


class AppSettings(BaseModel):
    pivot_projects: List[str]
    ignored_projects: List[str]
    dockerfile_argument_map: Dict[str, str]
    docker_suffixes: List[str]
    project_aliases: Dict[str, str]

    gitlab: GitlabSettings

    redis: RedisSettings


@lru_cache
def load_settings() -> AppSettings:
    with open("settings.yml", "r") as f:
        return AppSettings(**yaml.safe_load(f))
