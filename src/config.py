import os
import yaml

class Config:
    def __init__(self, config_file=None):
        if config_file is None:
            config_file = os.path.join(os.path.dirname(__file__), '../config.yml')
        with open(config_file, 'r') as file:
            self.config = yaml.safe_load(file)

    def get_debugging(self, component):
        return self.config.get('debugging', {}).get(component, False)

config = Config()

def debug_print(component, message):
    if config.get_debugging(component):
        print(message)
