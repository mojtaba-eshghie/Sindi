import os
import yaml
import inspect
from colorama import init, Fore

init(autoreset=True)

class Config:
    def __init__(self, config_file=None):
        if config_file is None:
            config_file = os.path.join(os.path.dirname(__file__), '../config.yaml')
        with open(config_file, 'r') as file:
            self.config = yaml.safe_load(file)

    def get_debugging(self, component):
        return self.config.get('debugging', {}).get(component, False)

config = Config()

def debug_print(message, is_exception=False):
    caller_frame = inspect.stack()[1]
    module = inspect.getmodule(caller_frame[0])
    component = module.__name__.split('.')[-1] if module else 'unknown'
    if config.get_debugging(component):
        if is_exception:
            print(Fore.RED + message)
        else:
            print(message)
