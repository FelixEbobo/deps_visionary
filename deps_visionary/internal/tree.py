import logging
import json
from pathlib import Path
from typing import Dict, Any

project_deps: Dict[str, Any] = {}


def build_tree_for_project(project_path: str, project_tag: str):
    tree: Dict[str, Any] = {}
    project_hash = f"{project_path}:{project_tag}"
    tree["name"] = project_hash
    tree["children"] = []

    if project_deps.get(project_hash):
        logging.debug("project %s found in cache", project_hash)
        return project_deps[project_hash]

    path = Path(f"projects/{project_path}/{project_tag}/project_dependencies.json")
    logging.info("Processing project %s %s", project_path, project_tag)

    if not path.exists():
        logging.warning("%s not exist", path)
        return tree

    with open(path, "r") as f:
        metadata = json.load(f)

    for deps_provider, dependency_map in metadata.items():
        if len(dependency_map) == 0:
            continue
        for project, version in dependency_map.items():
            dependencies = build_tree_for_project(project, version)
            dependencies["deps_provider"] = deps_provider
            project_deps[f"{project}:{version}"] = dependencies
            tree["children"].append(dependencies)
    return tree


def build_tree_for_project_with_group(project_path: str, project_tag: str):
    tree: Dict[str, Any] = {}
    project_hash = f"{project_path}:{project_tag}"
    tree["name"] = project_hash
    tree["children"] = []

    if project_deps.get(project_hash):
        logging.debug("project %s found in cache", project_hash)
        return project_deps[project_hash]

    path = Path(f"projects/{project_path}/{project_tag}/project_dependencies.json")
    logging.info("Processing project %s %s", project_path, project_tag)

    if not path.exists():
        logging.warning("%s not exist", path)
        return tree

    with open(path, "r") as f:
        metadata = json.load(f)

    for deps_provider, dependency_map in metadata.items():
        if len(dependency_map) == 0:
            continue
        children_of_deps_provides = []
        for project, version in dependency_map.items():
            add_obj = build_tree_for_project_with_group(project, version)
            add_obj["deps_provider"] = deps_provider
            project_deps[f"{project}:{version}"] = add_obj
            children_of_deps_provides.append(add_obj)
        tree["children"].append({"name": deps_provider, "children": children_of_deps_provides})
    return tree
