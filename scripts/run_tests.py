"""Run test suite."""

import subprocess
import sys

if __name__ == '__main__':
    result = subprocess.run(
        ['pytest', 'tests/', '-v', '--cov=.', '--cov-report=html'],
        cwd='.'
    )
    sys.exit(result.returncode)
