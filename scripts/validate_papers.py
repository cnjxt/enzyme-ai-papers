from __future__ import annotations

import sys

from paperlib import validate_all


def main() -> int:
    errors = validate_all()
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
