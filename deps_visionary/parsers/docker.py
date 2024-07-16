from dataclasses import dataclass, field
from typing import Dict, Tuple, List

from deps_visionary.internal.parser import BaseParser, remove_suffixes


@dataclass
class DockerfileParser(BaseParser, parser_type="dockerfile"):
    argument_map: Dict[str, str] = field(default_factory=lambda: {})

    @staticmethod
    def __is_line_suitable(line: str) -> bool:
        return line.startswith("ARG") or line.startswith("FROM")

    @staticmethod
    def __is_line_contains_argument(line: str) -> bool:
        return line.startswith("ARG") and line.find("=") != -1

    # TODO(felix_ebobo): Find better name for func
    @staticmethod
    def __is_line_contains_argument_usage(line: str) -> bool:
        return line.find("${") != -1

    @staticmethod
    def __extract_argument(line: str) -> List[str]:
        line = line.lstrip("ARG").replace(" ", "")
        return line.split("=", maxsplit=1)

    @staticmethod
    def __is_dependancy_in_line(line: str) -> bool:
        return line.startswith("FROM")

    def _save_argument(self, key: str, value: str) -> None:
        self.argument_map[key] = value

    def __substitute_argument(self, line: str) -> str:
        start_index = line.find("${")
        assert start_index != -1
        end_index = line.find("}", start_index)
        assert end_index != -1

        # Because substring ${ has two symbols
        key = line[start_index + 2 : end_index]
        assert key in self.argument_map
        # TODO(felix_ebobo): make more readable string format
        return line.replace(f"${{{key}}}", self.argument_map[key])

    @staticmethod
    def __parse_dependency_line(line: str) -> Tuple[str, str]:
        # FROM registry-path.net/team/project/some_repo:version AS python_builder
        # registry-path.net/team/project/some_repo:version
        # team/project/some_repo/suffix:version
        # team/project/some_repo:version

        splitted = line.split(" ")
        project_info = splitted[1].split("/", maxsplit=1)[-1]
        if project_info.find(":") != -1:
            project_path, version = project_info.split(":")
        else:
            # That means we use latest tag
            # FROM registry-path.net/team/project/some_repo AS python_builder
            project_path = project_info
            version = "latest"
        project_path = remove_suffixes(project_path)
        return project_path, version

    def parse_file(self) -> None:
        with open(self.file_path, "r") as f:
            lines_with_info = list(
                map(
                    lambda x: x.rstrip("\n"),
                    filter(self.__is_line_suitable, f.readlines()),
                )
            )

        for line in lines_with_info:
            while self.__is_line_contains_argument_usage(line):
                line = self.__substitute_argument(line)

            if self.__is_line_contains_argument(line):
                key, value = self.__extract_argument(line)
                self._save_argument(key, value)

            if self.__is_dependancy_in_line(line):
                project_path, version = self.__parse_dependency_line(line)
                self.save_dependency(project_path, version)
