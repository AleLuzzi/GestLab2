#!/usr/bin/env python
"""Punto di ingresso precedente, sostituito dall'onboarding ripetibile.

Non crea più un tenant di esempio. Usare:

    python -m saas.onboarding --help
"""

import sys


def main():
    print(
        "Questo script non crea più un tenant di esempio.\n"
        "Usa: python -m saas.onboarding --help",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
