#!/usr/bin/env python
"""Onboarding interno ripetibile di un laboratorio GestLab.

Crea tenant, dati OSA, primo admin e catalogo vuoto oppure il template
macelleria, senza SQL manuale.

Esempio::

    python -m saas.onboarding --nome "Macelleria Rossi" --piano basic ^
        --ragione-sociale "Rossi Carni Srl" --sede "Via Roma 1, Milano" ^
        --laboratorio "Laboratorio Rossi" --partita-iva 12345678901 ^
        --email admin@rossi.example --catalogo macelleria
"""

import argparse
import getpass
import sys

from pydantic import ValidationError

from saas.errori_operatore import messaggio_validazione
from saas.schemas import OnboardingRichiesta
from saas.services.onboarding import OnboardingError, crea_laboratorio


def _argomenti(argv):
    parser = argparse.ArgumentParser(
        description="Crea un laboratorio GestLab pronto per il login."
    )
    parser.add_argument("--nome", required=True, help="Nome del tenant")
    parser.add_argument(
        "--piano",
        default="basic",
        choices=("basic", "pro", "enterprise"),
        help="Piano contrattuale (default: basic)",
    )
    parser.add_argument("--ragione-sociale", required=True, help="Ragione sociale OSA")
    parser.add_argument("--sede", required=True, help="Indirizzo della sede OSA")
    parser.add_argument("--laboratorio", required=True, help="Nome del laboratorio")
    parser.add_argument("--partita-iva", required=True, help="Partita IVA di 11 cifre")
    parser.add_argument("--email", required=True, help="Email del primo amministratore")
    parser.add_argument(
        "--password",
        help="Password dell'amministratore. Se omessa, viene chiesta a video.",
    )
    parser.add_argument(
        "--catalogo",
        default="vuoto",
        choices=("vuoto", "macelleria"),
        help="Catalogo iniziale: vuoto oppure template macelleria",
    )
    return parser.parse_args(argv)


def main(argv=None):
    """Esegue l'onboarding e stampa gli id creati. Non ristampa la password."""
    args = _argomenti(sys.argv[1:] if argv is None else argv)
    password = args.password
    if not password:
        password = getpass.getpass("Password del primo admin: ")
        conferma = getpass.getpass("Ripeti la password: ")
        if password != conferma:
            print("Le password non coincidono.", file=sys.stderr)
            return 1
    try:
        richiesta = OnboardingRichiesta(
            nome=args.nome,
            piano=args.piano,
            ragione_sociale=args.ragione_sociale,
            indirizzo=args.sede,
            laboratorio=args.laboratorio,
            partita_iva=args.partita_iva,
            email=args.email,
            password=password,
            catalogo=args.catalogo,
        )
        esito = crea_laboratorio(richiesta)
    except ValidationError as exc:
        print(messaggio_validazione(exc.errors()), file=sys.stderr)
        return 1
    except OnboardingError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Laboratorio creato. Tenant ID: {esito['tenant_id']}")
    print(f"Admin ID: {esito['utente_id']}")
    print(f"Email: {esito['email']}")
    print(f"Catalogo: {esito['catalogo']} ({esito['articoli']} articoli)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
