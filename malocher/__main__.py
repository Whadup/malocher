"""
Run a job passed as first argument
"""
import sys
from .malocher import work
if __name__ == "__main__":
    JOB = sys.argv[1]
    work(JOB)
