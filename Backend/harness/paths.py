import os
from pathlib import Path

def get_project_root() -> str:
    """
    Returns the absolute path to the project root directory.
    Checks PROJECT_ROOT env var, walks up parent dirs looking for configs/variables.yaml,
    or falls back to the parent of the harness package.
    """
    if "PROJECT_ROOT" in os.environ and os.path.exists(os.environ["PROJECT_ROOT"]):
        return os.path.abspath(os.environ["PROJECT_ROOT"])
    
    # Check parent of current file (harness/.. -> Backend)
    curr = os.path.abspath(os.path.dirname(__file__))
    candidate = os.path.abspath(os.path.join(curr, ".."))
    if os.path.exists(os.path.join(candidate, "configs", "variables.yaml")):
        return candidate
        
    # Search upwards
    while curr and os.path.dirname(curr) != curr:
        if os.path.exists(os.path.join(curr, "configs", "variables.yaml")):
            return curr
        curr = os.path.dirname(curr)
        
    return os.path.abspath(os.getcwd())

def get_config_path(rel_path: str) -> str:
    return os.path.join(get_project_root(), "configs", rel_path)

def get_runs_path(rel_path: str = "") -> str:
    return os.path.join(get_project_root(), "runs", rel_path) if rel_path else os.path.join(get_project_root(), "runs")
