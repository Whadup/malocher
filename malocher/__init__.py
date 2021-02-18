"""
Malocher is a lightweight python library for running jobs on a cluster where nodes are accessed
via SSH and share a common network storage like traditional NFS or mountable cloud storage.

Author: Lukas Pfahler
Repo:   https://github.com/Whadup/malocher
"""
from .malocher import submit, process_all
