class FileReader:
    def __getitem__(self, item):
        try:
            lines = open(item, "r").readlines()
            return "\n".join(lines)
        except FileNotFoundError as fnfe:
            raise KeyError(str(item))
