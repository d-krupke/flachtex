import os.path


class FileReader:
    def __getitem__(self, item):
        try:
            if not os.path.exists(item) or not os.path.isfile(item):
                raise KeyError(str(item))
            lines = open(item, "r").readlines()
            return "\n".join(lines)
        except FileNotFoundError as fnfe:
            raise KeyError(str(item))
