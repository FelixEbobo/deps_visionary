from dataclasses import dataclass, field
from typing import Dict, Type
from pathlib import Path
from deps_visionary.internal.settings import load_settings
from deps_visionary.gitlabmgr.models import ProjectSearchModel


def remove_suffixes(project_path: str) -> str:
    for suffix in load_settings().docker_suffixes:
        if project_path.find(suffix) != -1:
            return project_path.removesuffix(suffix).removesuffix("/")
    return project_path


@dataclass
class BaseParser:
    file_path: str
    project_path: str
    dependencies_map: Dict[str, str] = field(default_factory=lambda: {})

    def __init_subclass__(cls, parser_type: str):
        ParserFactory.register(parser_type, parser_class=cls)

    def save_dependency(self, project_path: str, version: str):
        aliases_map = load_settings().project_aliases
        if project_path in aliases_map.keys():
            project_path = aliases_map[project_path]

        # it is a sign for a circular dependency which will break recursion :)
        if project_path == self.project_path:
            return
        self.dependencies_map[project_path] = version

    def parse_file(self) -> None:
        pass


class ParserFactory:
    __parser_dispatcher: Dict[str, Type[BaseParser]] = {}

    @classmethod
    def get(cls, parser_type: str, project_path: str, file_path: str, **kwargs) -> BaseParser:
        try:
            return cls.__parser_dispatcher[parser_type](file_path, project_path, **kwargs)
        except KeyError:
            # pylint: disable=raise-missing-from
            raise KeyError(f"unknown parser type: {parser_type}")

    @classmethod
    def register(cls, parser_type: str, parser_class: Type[BaseParser]):
        cls.__parser_dispatcher[parser_type] = parser_class


# pylint: disable=wrong-import-position,wildcard-import,unused-wildcard-import
from deps_visionary.parsers import *


def get_parser_by_filename(filename: str, project: ProjectSearchModel, file_path: str, **kwargs) -> BaseParser:
    assert filename.find("/") == -1
    return ParserFactory.get(Path(filename).stem.lower(), project.path_with_namespace, file_path, **kwargs)
