from flachtex.parser import Flattener, FileGuesser
from flachtex.filereader import FileReader
import sys

from flachtex.rules import NativeIncludeRule, ExplicitImportRule, SubimportRule, \
    BasicSkipRule

if __name__ == "__main__":
    file_guesser = FileGuesser(FileReader())
    include_rules = [NativeIncludeRule(), ExplicitImportRule(), SubimportRule()]
    skip_rules = [BasicSkipRule()]
    flattener = Flattener(file_guesser=file_guesser, include_rules=include_rules,
                          skip_rules=skip_rules)
    flattened = str(flattener.flatten(sys.argv[1]))
    #print(flattened)
