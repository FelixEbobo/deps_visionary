import ast
from typing import Tuple

from deps_visionary.internal.parser import BaseParser


class ConanfileParser(BaseParser, parser_type="conanfile"):

    class ConanFileClassVisitor(ast.NodeVisitor):
        def __init__(self):
            self.requires: Tuple[str] = tuple()
            self.current_class = None

        # pylint: disable=invalid-name
        def visit_ClassDef(self, node):
            self.current_class = node.name
            self.generic_visit(node)

        # pylint: disable=invalid-name
        def visit_Assign(self, node):
            if not self.current_class:
                self.generic_visit(node)
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in (
                    "requires",
                    "tool_requires",
                    "build_requires",
                ):
                    if isinstance(node.value, ast.Constant):
                        self.requires = self.requires + tuple((node.value.s,))
                    if isinstance(node.value, ast.Tuple):
                        self.requires = self.requires + tuple(str(element.s) for element in node.value.elts)
            self.generic_visit(node)

    def _parse_conanfile_py_file(self) -> None:
        with open(self.file_path, "r") as f:
            content = f.read()
        tree = ast.parse(content)

        visitor = self.ConanFileClassVisitor()
        visitor.visit(tree)

        for dependency in visitor.requires:
            package_name, package_version = self._parse_conanfile_require_line(dependency)
            self.save_dependency(package_name, package_version)

    @staticmethod
    def _parse_conanfile_require_line(line) -> Tuple[str, str]:
        # library_name/6.1.6@remote/name
        # library_name/6.1.6
        # ("library_name", "6.1.6")
        package = line.split("@", maxsplit=1)[0]
        return package.split("/", maxsplit=1)

    def _parse_conanfile_txt_file(self) -> None:
        with open(self.file_path, "r") as f:
            parse_enabled = False

            for line in f.readlines():
                line = line.rstrip("\n")
                if line == "[requires]":
                    parse_enabled = True
                    continue

                if not parse_enabled:
                    continue

                if len(line) == 0:
                    continue

                # When we walked throug [requires] block and another block starts - exit
                if line.startswith("[") and line.endswith("]") and parse_enabled:
                    return

                if parse_enabled:
                    package_name, package_version = self._parse_conanfile_require_line(line)

                    self.save_dependency(package_name, package_version)

    def parse_file(self) -> None:
        if self.file_path.endswith(".py"):
            self._parse_conanfile_py_file()
        else:
            self._parse_conanfile_txt_file()
