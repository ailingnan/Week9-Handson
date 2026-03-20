import os
import yaml
from typing import Any, Dict

def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """Loads the YAML configuration file."""
    # Find project root (assuming this file is in core/)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    full_path = os.path.join(project_root, config_path)
    
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Configuration file not found at: {full_path}")
        
    with open(full_path, "r") as f:
        return yaml.safe_load(f)

# Global settings dict to be imported by other modules
SETTINGS = load_config()
