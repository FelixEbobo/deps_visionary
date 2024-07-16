import os
import logging
from http import HTTPStatus

from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse

from deps_visionary.api.models import ProcessProjectTagRequest
from deps_visionary.internal import projects_metadata
from deps_visionary.internal.tree import build_tree_for_project
from deps_visionary.internal.settings import load_settings
from deps_visionary.tasks import process_project_tag_task, redis


def create_app() -> FastAPI:
    prefix_router = APIRouter()

    @prefix_router.get("/project/deps")
    async def get_project_deps(project_path: str, project_tag: str):
        if not os.path.exists(f"projects/{project_path}/{project_tag}/project_dependencies.json"):
            return JSONResponse(
                content={"message": f"No processed dependencies were found for {project_path} {project_tag}"},
                status_code=HTTPStatus.NOT_FOUND,
            )

        return build_tree_for_project(project_path, project_tag)

    @prefix_router.get("/project/tags")
    async def get_project_tags(project_path: str):
        if not projects_metadata.is_project_dir_exist(project_path):
            return JSONResponse(
                content={"message": f"No tags cache found for project {project_path}"},
                status_code=HTTPStatus.NOT_FOUND,
            )

        return projects_metadata.read_project_tags_cache(project_path)

    @prefix_router.post("/project/process_tag")
    async def process_project_tag(project_request: ProcessProjectTagRequest):
        if not os.path.exists(
            f"projects/{project_request.project_path}/{project_request.project_tag}/project_dependencies.json"
        ):
            logging.debug(
                "Project metadata for %s:%s doesn't exist, creating task",
                project_request.project_path,
                project_request.project_tag,
            )
            lock_name = f"process_{project_request.project_path}_{project_request.project_tag}"
            lock = redis.get(lock_name)
            if lock:
                return JSONResponse(
                    content={"message": "This project tag is already being processed"},
                    status_code=HTTPStatus.BAD_REQUEST,
                )

            process_project_tag_task.apply_async(
                [project_request.project_path, project_request.project_tag],
                {"lock_name": lock_name},
            )

            return JSONResponse(
                content={"message": "Started processing project tag"},
            )

        return JSONResponse(
            content={"message": "This project tag has been already processed earlier"},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    @prefix_router.get("/pivot_projects")
    async def get_pivot_projects():
        return JSONResponse(content=load_settings().pivot_projects)

    app = FastAPI(openapi_url=None)
    app.include_router(prefix_router, prefix="/api/depsvis/v1")

    return app
