#!/bin/bash
#
# This script ensures that the star topology tests are always run
# from the project's root directory.
#
cd "$(dirname "$0")"
.venv/bin/python3 -m pytest tests/test_star_topology.py -v