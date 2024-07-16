import os
import json
from pathlib import Path
from typing import Dict, Any, List
from deps_visionary.gitlabmgr.models import ProjectTagList, ProjectTag

BASE_PROJECTS_FOLDER = "projects"


def setup_metadata_folder() -> None:
    os.makedirs(BASE_PROJECTS_FOLDER, exist_ok=True)


def create_project_folder(project_path: str) -> None:
    os.makedirs(f"{BASE_PROJECTS_FOLDER}/{project_path}", exist_ok=True)
    path = f"{BASE_PROJECTS_FOLDER}/{project_path}/project_tags.json"
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(json.dumps({}))


def create_project_tag(project_path: str, project_tag: str) -> None:
    tag_path = f"{BASE_PROJECTS_FOLDER}/{project_path}/{project_tag}"
    os.makedirs(tag_path, exist_ok=True)


def create_project_tags(project_path: str, project_tags: ProjectTagList) -> None:
    for tag in project_tags:
        create_project_tag(project_path, tag.name)


def is_project_tags_cache_exist(project_path: str) -> bool:
    return os.path.exists(f"{BASE_PROJECTS_FOLDER}/{project_path}/project_tags.json")


def read_project_tags_cache(project_path: str) -> List[str]:
    path = Path(f"{BASE_PROJECTS_FOLDER}/{project_path}")

    result = []
    for tag in path.iterdir():
        if tag.is_file():
            continue
        result.append(tag.name)

    result.sort(reverse=True)
    return result


def add_to_project_tags_cache(project_path: str, tag: ProjectTag) -> None:
    path = f"{BASE_PROJECTS_FOLDER}/{project_path}/project_tags.json"

    json_data = {}

    with open(path, "rb") as f:
        json_data = json.load(f)

    if not json_data.get(tag.name):
        json_data[tag.name] = tag.dict()

        with open(path, "w") as f:
            f.write(json.dumps(json_data, indent=2))


def save_file(project_path: str, project_tag: str, file_name: str, file_content: bytes) -> str:
    path = f"{BASE_PROJECTS_FOLDER}/{project_path}/{project_tag}/{file_name}"
    with open(path, "wb") as f:
        f.write(file_content)

    return path


def save_empty_dependencies(project_path: str, project_tag: str) -> None:
    path = f"{BASE_PROJECTS_FOLDER}/{project_path}/{project_tag}/project_dependencies.json"

    with open(path, "w") as f:
        json.dump({}, f)


def add_dependecnies_metadata(
    project_path: str, project_tag: str, metadata_key: str, dependencies: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge JSON file project_dependencies.json with value of `dependencies` under key `metadata_key`
    """
    path = f"{BASE_PROJECTS_FOLDER}/{project_path}/{project_tag}/project_dependencies.json"

    json_data = {}

    if os.path.exists(path):
        with open(path, "rb") as f:
            json_data = json.load(f)

    json_data = json_data | {metadata_key: dependencies}

    with open(path, "w") as f:
        json.dump(json_data, f)

    return json_data


def get_dependecnies_metadata(project_path: str, project_tag: str) -> Dict[str, Any]:
    """
    Reads JSON file project_dependencies.json and returns its content
    """

    path = f"{BASE_PROJECTS_FOLDER}/{project_path}/{project_tag}/project_dependencies.json"
    with open(path, "rb") as f:
        return json.load(f)


def is_depedencies_metadata_exist(project_path: str, project_tag: str) -> bool:
    """
    Checks if JSON file project_dependencies.json for project exists
    """
    return Path(f"{BASE_PROJECTS_FOLDER}/{project_path}/{project_tag}/project_dependencies.json").exists()


def is_project_dir_exist(project_path) -> bool:
    return Path(f"{BASE_PROJECTS_FOLDER}/{project_path}").exists()
