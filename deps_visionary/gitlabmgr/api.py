from http import HTTPStatus
import logging
import re
from typing import Optional
from urllib.parse import quote_plus

import requests

from deps_visionary.gitlabmgr.models import (
    ProjectSearchModelList,
    ProjectsCacheModel,
    ProjectSearchModel,
    ProjectTagList,
    ProjectFileList,
)
from deps_visionary.internal.settings import load_settings


def make_gitlab_url(uri: str) -> str:
    return load_settings().gitlab.url + "api/v4/" + uri


def request_to_gitlab(uri: str, raise_for_status: bool = True) -> requests.Response:
    logging.info("Sending request to projects")
    headers = {"Authorization": f"Bearer {load_settings().gitlab.token}"}
    response = requests.get(make_gitlab_url(uri), headers=headers)
    logging.debug("Response code is %d", response.status_code)
    if raise_for_status:
        response.raise_for_status()
    return response


# /api/v4/projects?search_namespaces=true&search=isp_daemon&order_by=last_activity_at&sort=asc
def find_project(project_name: str) -> Optional[ProjectSearchModel]:
    logging.info("Searching for a project with name %s", project_name)

    logging.debug("Trying to find project in cache")
    with open("projects_cache.json", "r") as f:
        projects_cache = ProjectsCacheModel.model_validate_json(f.read())
        if project := projects_cache.root.get(project_name):
            logging.debug("Project with ID %d was found", project.id)
            return project

    logging.debug("Project was not found in cache, querying from gitlab")

    response = request_to_gitlab(
        f"projects?search_namespaces=true&search={project_name}&orderby=last_activity_at&sort=desc"
    )
    projects = ProjectSearchModelList.model_validate_json(response.content)
    if len(projects.root) == 0:
        logging.warning("No project under name %s was found", project_name)
        return None

    found_project = projects.root[0]

    if len(projects.root) > 1:
        logging.warning("More than one projects were found, trying to find project with the same name")
        for project in projects:
            if project_name in (project.name, project.path_with_namespace):
                found_project = project

    logging.debug("Saving project info into cache")
    projects_cache.root[project_name] = found_project
    with open("projects_cache.json", "w") as f:
        f.write(projects_cache.model_dump_json())

    return found_project


def is_there_tags(project_id: int, project_tag: str) -> bool:
    response = request_to_gitlab(
        f"projects/{project_id}/repository/tags?order_by=version&sort=desc&search={project_tag}"
    )
    if response.status_code == HTTPStatus.NOT_FOUND:
        return False

    project_tags = ProjectTagList.model_validate_json(response.content)
    if len(project_tags.root) == 0:
        return False

    return True


# TODO(felix_ebobo): cache tag formats
def get_project_tag_format(project_id: int, project_tag: str) -> str:
    default_tag_format = "{0}"

    if project_tag == "latest" or project_tag == "master" or not re.search(r"\d+\.\d+\.\d+", project_tag):
        return default_tag_format

    logging.info("Retriving last tag for #%d to determine tag format", project_id)
    response = request_to_gitlab(
        f"projects/{project_id}/repository/tags?order_by=version&sort=desc&search={project_tag}"
    )

    project_tags = ProjectTagList.model_validate_json(response.content)
    if len(project_tags.root) == 0:
        logging.warning("project has no tags")
        return default_tag_format

    last_tag = project_tags.root[0]
    if last_tag.name.startswith("v"):
        logging.debug("Tag format is vX.X.X")
        return "v{0}"
    return default_tag_format


def get_project_tags(project_id: int) -> ProjectTagList:
    """
    Retrive 3 last tags from project
    """
    logging.info("Retriving 3 last tags from project #%d", project_id)
    response = request_to_gitlab(f"projects/{project_id}/repository/tags?order_by=version&sort=desc")

    project_tags = ProjectTagList.model_validate_json(response.content)

    project_tags.root = project_tags.root[:3]

    return project_tags


# TODO(felix_ebobo): Need to do something with multy dependencies of python, e.g. >=1.0, <3
def get_project_files_from_tag(project_id: int, project_tag: str, tag_format="{0}") -> ProjectFileList:
    if project_tag == "latest":
        project_tag = "master"

    logging.info("Retriving file list from root directory for project #%d and tag %s", project_id, project_tag)
    response = request_to_gitlab(
        f"projects/{project_id}/repository/tree?ref={tag_format.format(project_tag)}&per_page=75",
        raise_for_status=False,
    )
    if response.status_code == HTTPStatus.NOT_FOUND:
        return ProjectFileList([])

    project_files = ProjectFileList.model_validate_json(response.content)

    return project_files


# TODO: download blob instead of raw
def get_project_file(project_id: int, project_tag: str, file_path: str, tag_format="{0}") -> bytes:
    if project_tag == "latest":
        project_tag = "master"

    logging.info("Getting file %s content from project #%d and tag %s", file_path, project_id, project_tag)
    response = request_to_gitlab(
        f"projects/{project_id}/repository/files/{quote_plus(file_path)}/raw?ref={tag_format.format(project_tag)}"
    )

    return response.content
