"""EcomInsights API application."""

import os
import sys

# Ensure ml/src and backend root are on sys.path so ecominsights_ml is discoverable
# even when executed from Anaconda or outside virtual environments.
_app_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_app_dir)
_repo_root = os.path.dirname(_backend_dir)
_ml_src = os.path.join(_repo_root, "ml", "src")

for _p in (_backend_dir, _ml_src):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

