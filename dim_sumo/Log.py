
from SimStateAndConfig import SimStateAndConfig 
import re

class Log:

    def __init__(self, config : SimStateAndConfig):
        self.config = config
        self.filter = None if config.log_filter_regex is None else re.compile(config.log_filter_regex)

    def info(self, source, *message):
        if self.config.log_info:
            self.__print_with_filter(source, message)
    
    def debug(self, source, *message):
        if self.config.log_debug:
            self.__print_with_filter(source, message)

    def __print_with_filter(self, source, *message):
        if self.filter is None or self.filter.match(str(source)):
            print(self.config.current_step, source, message)

    