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

def debug_print(message, type_=False):
    caller_frame = inspect.stack()[1]
    module = inspect.getmodule(caller_frame[0])
    component = module.__name__.split('.')[-1] if module else 'unknown'
    if config.get_debugging(component):
        if type_ == 'exception':
            print(Fore.RED + message)
        elif type_ == 'info':
            print(Fore.GREEN + message)
        elif type_ == 'neutral':
            print(Fore.YELLOW + message)
        else:
            print(message)
