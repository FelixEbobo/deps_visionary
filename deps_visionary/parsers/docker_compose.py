import logging
import yaml

from deps_visionary.internal.parser import BaseParser, remove_suffixes


class DockerComposeParser(BaseParser, parser_type="docker-compose"):

    @staticmethod
    def __explode_line(image_value: str):
        # registry-path.net/team/project/some_repo:version
        # registry-path.net/team/project/some_repo:version
        # team/project/some_repo/suffix:version
        # team/project/some_repo:version

        project_info = image_value.split("/", maxsplit=1)[-1]
        project_path, version = project_info.split(":")
        project_path = remove_suffixes(project_path)
        return project_path, version

    def parse_file(self) -> None:
        with open(self.file_path, "r") as f:
            docker_compose_data = yaml.safe_load(f)

        for service, data in docker_compose_data["services"].items():
            if "build" in data:
                logging.warning("%s has build context, skipping", service)
                continue
            if "image" in data:
                project_path, version = self.__explode_line(data["image"])
                self.save_dependency(project_path, version)
            else:
                logging.warning("%s has no image", service)
