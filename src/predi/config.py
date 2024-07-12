import os
import yaml
import inspect
from colorama import init, Fore

init(autoreset=True)

class Config:
    _instance = None
    _default_config = {
        'debugging': {
            'tokenizer': False,
            'parser': False,
            'simplifier': False,
            'solver': False,
            'cli': False,
        }
    }

    def __new__(cls, config_file=None):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialize(config_file)
        return cls._instance

    def _initialize(self, config_file):
        self.config = Config._default_config

        if config_file:
            config_file = os.path.join(os.path.dirname(__file__), config_file)
            if os.path.exists(config_file):
                with open(config_file, 'r') as file:
                    self.config.update(yaml.safe_load(file))

    def get_debugging(self, component):
        return self.config.get('debugging', {}).get(component, False)

    def debug_print(self, message, type_=False):
        caller_frame = inspect.stack()[1]
        module = inspect.getmodule(caller_frame[0])
        component = module.__name__.split('.')[-1] if module else 'unknown'
        if self.get_debugging(component):
            if type_ == 'exception':
                print(Fore.RED + message)
            elif type_ == 'info':
                print(Fore.GREEN + message)
            elif type_ == 'neutral':
                print(Fore.YELLOW + message)
            else:
                print(message + Fore.RESET + '\n ------------------------------------------------------------ ')

config = Config()

def debug_print(message, type_=False):
    config.debug_print(message, type_)
