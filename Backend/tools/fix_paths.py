import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def patch_file(path, replacements):
    full_path = os.path.join(ROOT, path)
    if not os.path.exists(full_path):
        print(f"Skipping {path} (not found)")
        return
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()
    orig = content
    for old, new in replacements:
        content = content.replace(old, new)
    if content != orig:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Patched: {path}")
    else:
        print(f"No changes needed: {path}")

# Fix imports in hawkes.py
patch_file("cascade/hawkes.py", [
    ("from typing import Dict, Any, List, Tuple, Optional", "from typing import Dict, Any, List, Tuple, Optional\nfrom harness.paths import get_project_root"),
    ("os.path.join(get_project_root(), 'training code/hawkes_model',", "os.path.join(get_project_root(), 'training code', 'hawkes_model'),")
])

# Fix imports in risk/gbm.py
patch_file("risk/gbm.py", [
    ("from typing import Dict, Any, List, Tuple, Optional", "from typing import Dict, Any, List, Tuple, Optional\nfrom harness.paths import get_project_root"),
    ("os.path.join(get_project_root(), 'training code/lgbm_models',", "os.path.join(get_project_root(), 'training code', 'lgbm_models'),")
])

# Fix imports in cascade/etas.py
patch_file("cascade/etas.py", [
    ("from typing import Dict, Any, List, Tuple, Optional", "from typing import Dict, Any, List, Tuple, Optional\nfrom harness.paths import get_project_root"),
    ("os.path.join(get_project_root(), 'training code/etas_model',", "os.path.join(get_project_root(), 'training code', 'etas_model'),")
])

# Fix imports in eval/report.py
patch_file("eval/report.py", [
    ("from typing import Dict, Any, List", "from typing import Dict, Any, List\nfrom harness.paths import get_project_root")
])

# Fix sim/gen_episodes.py
patch_file("sim/gen_episodes.py", [
    ("from harness.faults import FaultInjector", "from harness.faults import FaultInjector\nfrom harness.paths import get_project_root")
])

print("Paths and imports fixed.")
