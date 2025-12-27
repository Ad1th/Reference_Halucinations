#!/usr/bin/env python3
import sys
import os

# Add src to python path so we can import our package
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from ref_hal.cli import main

if __name__ == "__main__":
    main()
