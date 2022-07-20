import os.path
import typing


class FileSystem:
    """
    Wraps the file system access such that it could be replaced with a simple dict
    to ease testing.
    """

    def __contains__(self, item) -> bool:
        return os.path.exists(item) and os.path.isfile(item)

    def __getitem__(self, item) -> str:
        if not item in self:
            raise KeyError(f"Could not find {item}.")
        with open(item, "r") as f:
            return "".join(f.readlines())


class FileFinder:
    def __init__(self, project_root=".", file_system=None):
        """
        :param project_root: The root of the project (relative to cwd)
        :param file_system: A module to open files, can be replaced with a simple dict
            for simple testing.
        """
        if not file_system:
            file_system = FileSystem()
        self.file_system = file_system
        self._PATH = [project_root]
        self._project_root = project_root

    def set_root(self, project_root: str):
        self._PATH = [project_root]

    def find_best_matching_path(self, path: str, origin: str) -> str:
        """
        Returns the best path relative to the current working directory that resolves the
        wanted path, which is not necessarily relative to the current working directory.
        :param path: Path to be resolved.
        :param origin: The path to the file (relative to cwd) that tries to open above's
            path.
        :return:
        """
        for p in self.get_checked_paths(path, origin):
            if p in self.file_system:
                return p
        raise KeyError(
            f"Not matching file found. "
            f"Tried: {', '.join(self.get_checked_paths(path, origin))}"
        )

    def _normalize(self, path: str):
        return os.path.normpath(path)

    def get_checked_paths(self, path: str, origin: str) -> typing.Iterable[str]:
        """
        Returns all paths that will be tried to find the file.
        :param path: Path to the file. Not necessarily regarding the current working
                        directory.
        :param origin: Path of the file that tries to access above's path
        :return: The best matching path to the file relative to the current working
                    directory, i.e., can be opened directly.
        """
        # if it is an absolute path, try this one first
        if os.path.isabs(path):
            yield os.path.normpath(path)
            yield os.path.normpath(path) + ".tex"
        # then try to go relative from the origin file
        d = os.path.dirname(origin)
        yield self._normalize(os.path.join(d, path))
        yield self._normalize(os.path.join(d, path)) + ".tex"
        # then try to use the include directories
        for include in self._PATH:
            yield self._normalize(os.path.join(include, path))
            yield self._normalize(os.path.join(include, path)) + ".tex"
        # finally, in a last attempt, go upwards from the origin file
        while d != self._project_root:  # stop if the root directory has been reached
            yield self._normalize(os.path.join(d, path))
            yield self._normalize(os.path.join(d, path)) + ".tex"
            d = os.path.dirname(d)  # go one directory above

    def read(self, path) -> str:
        """
        Just returns the content of the path as a single string.
        :param path: Path to the file
        :return: File content
        """
        return self.file_system[self._normalize(path)]
