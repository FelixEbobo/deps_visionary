from pip._internal.network.session import PipSession
from pip._internal.req import parse_requirements
from pip._internal.req import constructors

from deps_visionary.internal.parser import BaseParser


class RequirementsParser(BaseParser, parser_type="requirements"):

    def parse_file(self) -> None:
        data = parse_requirements(self.file_path, session=PipSession())
        for req in data:
            install_req = constructors.install_req_from_parsed_requirement(req)

            if len(install_req.specifier) == 0:
                self.save_dependency(str(install_req.name), "latest")
            else:
                for spec in install_req.specifier:
                    self.save_dependency(str(install_req.name), spec.version)
