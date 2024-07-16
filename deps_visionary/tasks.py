import logging
from contextlib import contextmanager

import redis
from redis.lock import Lock
from celery import Celery, group
from celery.schedules import crontab

from deps_visionary.internal.settings import load_settings, SUPPORTED_FILES
from deps_visionary.gitlabmgr import api as gitlab_api
from deps_visionary.internal import projects_metadata

from deps_visionary.gitlabmgr.models import ProjectFile
from deps_visionary.internal.parser import get_parser_by_filename

celery = Celery(__name__)
settings = load_settings()
celery.conf.broker_url = settings.redis.url
celery.conf.result_backend = settings.redis.url

redis = redis.Redis.from_url(settings.redis.url)


@contextmanager
def redis_lock(lock_name: str = "simple_lock"):
    logging.debug("Creating lock '%s'", lock_name)
    lock: Lock = redis.lock(
        lock_name,
        sleep=5,
        timeout=settings.redis.lock_max_time * 60,
        blocking_timeout=(settings.redis.lock_max_time + 5) * 60,
    )

    logging.debug("Acquiring lock '%s'", lock_name)
    try:
        lock_acquired = lock.acquire()
        logging.debug("Acquiring was successful? %r", lock_acquired)
        if not lock_acquired:
            raise RuntimeError(f"Lock '{lock_name}' hasn't been acquired")
        yield lock_acquired

    finally:
        logging.debug("Releasing lock '%s'", lock_name)
        lock.release()
        logging.debug("Lock '%s' has been released", lock_name)


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **_):
    sender.add_periodic_task(
        crontab(minute=0, hour="*/1"),
        check_new_tags_for_pivot.s(),
    )


@celery.task(name="check_new_tags_for_pivot_project")
def check_new_tags_for_pivot():
    for pivot_project in load_settings().pivot_projects:
        logging.info("Processing pivot_project: %s", pivot_project)
        project = gitlab_api.find_project(pivot_project)
        if not project:
            logging.error("Failed to find pivot project")
            raise RuntimeError("Failed to find pivot project")
        projects_metadata.create_project_folder(project.path_with_namespace)

        tags = gitlab_api.get_project_tags(project.id)
        projects_metadata.create_project_tags(project.path_with_namespace, tags)

        tag_tasks = []
        for tag in tags:
            logging.info("Processing tag %s", tag.name)
            projects_metadata.create_project_tag(project.path_with_namespace, tag.name)
            if projects_metadata.is_depedencies_metadata_exist(project.path_with_namespace, tag.name):
                logging.info("Tag dependencies already exist")
                continue
            logging.info("Tag dependencies doesn't exist, begin processing")
            tag_tasks.append(process_project_tag_task.s(project.path_with_namespace, tag.name))

        task_group = group(tag_tasks)
        result = task_group.apply_async()
        logging.info("Were all tasks completed? %r", result.ready())
        logging.info("Were all tasks successfull? %r", result.successful())

    return True


def file_filter(file: ProjectFile) -> bool:
    return file.name in SUPPORTED_FILES


# Need to divide process_project task and process project
@celery.task(name="process_project")
def process_project_tag_task(project_path: str, project_tag: str, lock_name: str = "process_project_tag_task") -> None:
    with redis_lock(lock_name=lock_name) as _:
        process_project_tag(project_path, project_tag)


def process_project_tag(project_path: str, project_tag: str):
    if project_path in settings.ignored_projects:
        logging.info("Project %s is in ignored projects list, skipping", project_path)
        return

    logging.info("Processing project: %s == %s", project_path, project_tag)
    project = gitlab_api.find_project(project_path)

    # Not found project in gitlab, breaking from recursion
    if not project:
        return

    if projects_metadata.is_depedencies_metadata_exist(project.path_with_namespace, project_tag):
        logging.debug("Dependencies metadata already exists, exiting")
        return

    projects_metadata.create_project_folder(project.path_with_namespace)

    projects_metadata.create_project_tag(project.path_with_namespace, project_tag)
    if not gitlab_api.is_there_tags(project.id, project_tag):
        logging.warning("Project has no tags, probably nothing interesting here")
        return

    tag_format = gitlab_api.get_project_tag_format(project.id, project_tag)
    files = gitlab_api.get_project_files_from_tag(project.id, project_tag, tag_format)

    filtered_file_list = list(filter(file_filter, files))
    if len(filtered_file_list) == 0:
        logging.warning("Not found interesting files in projects, saving empty dependencies data and exit")
        projects_metadata.save_empty_dependencies(project.path_with_namespace, project_tag)
        return

    metadata = {}
    for file in filtered_file_list:
        if file.mode == "120000":
            logging.debug("File %s is a symlink", file.name)
            file_content = gitlab_api.get_project_file(project.id, project_tag, file.path, tag_format)
            file.path = file_content.decode("utf-8").lstrip("./")
        file_content = gitlab_api.get_project_file(project.id, project_tag, file.path, tag_format)
        file_path = projects_metadata.save_file(project.path_with_namespace, project_tag, file.name, file_content)

        if file.name.lower().startswith("dockerfile"):
            parser = get_parser_by_filename(
                file.name,
                project,
                file_path,
                argument_map=settings.dockerfile_argument_map,
            )
        else:
            parser = get_parser_by_filename(file.name, project, file_path)

        parser.parse_file()

        metadata = projects_metadata.add_dependecnies_metadata(
            project.path_with_namespace, project_tag, file.name, parser.dependencies_map
        )

    for deps_provider, dependencies in metadata.items():
        logging.info("Processing dependencies of %s", deps_provider)
        for project_name, version in dependencies.items():

            if project_name in settings.project_aliases:
                logging.debug(
                    "Found alias for project %s %s",
                    project_name,
                    settings.project_aliases[project_name],
                )
                project_name = settings.project_aliases[project_name]

            process_project_tag(project_name, version)
