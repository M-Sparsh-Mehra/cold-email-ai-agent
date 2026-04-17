import yaml
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def load_yaml(file_path):
    """loads a YAML file and returns it as a Python dict."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {file_path}")
        return {}
    except Exception as e:
        logging.error(f"Error parsing YAML file {file_path}: {e}")
        return {}