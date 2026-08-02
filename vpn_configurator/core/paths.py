import os
import sys


def project_root():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def data_dir(*parts):
    return os.path.join(project_root(), "data", *parts)
