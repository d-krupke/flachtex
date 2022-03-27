from flachtex.comments import remove_comments
from flachtex.parser import expand_file
import sys

if __name__ == "__main__":
    print(remove_comments(expand_file(sys.argv[1])))
