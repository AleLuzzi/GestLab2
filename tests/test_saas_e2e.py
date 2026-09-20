"""Test end-to-end (S14) per il backend SaaS GestLab.

Verifica il flusso completo: bootstrap tenant/utente, login, auth JWT/bcrypt,
generazione DDT/scontrino/etichetta, barcode EAN e coda di stampa con
Local Print Agent flow.

Esecuzione:
    python tests/test_saas_e2e.py
"""

import os
import sys

# Assicura che il progetto sia nel path (se eseguito da altrove).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import connection
from saas import auth, tenant_repo, print_repo
from core.services import (
    printing,
    barcode,
    reparti as reparti_service,
    fornitori as fornitori_service,
    tagli as tagli_service,
)

RES = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"

_passed = 0
_failed = 0


def check(cond, msg):
    """Registra un esito del test."""
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  {GREEN}OK{RES}  {msg}")
    else:
        _failed += 1
        print(f"  {RED}FAIL{RES}  {msg}")


# ------------------------------------------------------------------------- #
#  Bootstrap del DB multi-tenant (una tantum, idempotente)
# ------------------------------------------------------------------------- #
def _crea_tabelle(c):
    """Crea le tabelle multi-tenant, ricreandole da zero (schema SaaS).

    NOTA: le tabelle SaaS (tenant, utenti, dispositivi_stampa, print_jobs)
    sono nuove rispetto al DB del progetto originale. Per garantire uno schema
    coerente e idempotente nel test, vengono droppate e ricreate. In
    produzione la creazione e' governata da ``saas/schema_multitenant.sql``.
    """
    # Drop in ordine di dipendenza (figlie prima dei padri).
    c.execute("DROP TABLE IF EXISTS print_jobs")
    c.execute("DROP TABLE IF EXISTS dispositivi_stampa")
    c.execute("DROP TABLE IF EXISTS utenti")
    c.execute("DROP TABLE IF EXISTS tenant")

    c.execute(
        "CREATE TABLE IF NOT EXISTS tenant ("
        "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
        "nome VARCHAR(255) NOT NULL,"
        "piano VARCHAR(50) DEFAULT 'basic',"
        "attivo BOOLEAN DEFAULT TRUE,"
        "creato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS utenti ("
        "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
        "tenant_id BIGINT,"
        "email VARCHAR(255) NOT NULL UNIQUE,"
        "password_hash VARCHAR(255) NOT NULL,"
        "ruolo VARCHAR(20) NOT NULL DEFAULT 'operatore',"
        "attivo BOOLEAN DEFAULT TRUE,"
        "creato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
        "CONSTRAINT fk_utenti_tenant FOREIGN KEY (tenant_id) REFERENCES tenant(id))"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS dispositivi_stampa ("
        "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
        "tenant_id BIGINT NOT NULL,"
        "nome VARCHAR(255) NOT NULL,"
        "token VARCHAR(255) NOT NULL UNIQUE,"
        "stampante_dymo VARCHAR(255),"
        "stampante_termica VARCHAR(255),"
        "ultimo_heartbeat TIMESTAMP NULL,"
        "CONSTRAINT fk_dispositivi_tenant FOREIGN KEY (tenant_id) REFERENCES tenant(id))"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS print_jobs ("
        "id BIGINT PRIMARY KEY AUTO_INCREMENT,"
        "tenant_id BIGINT NOT NULL,"
        "dispositivo_id BIGINT NULL,"
        "tipo VARCHAR(20) NOT NULL,"
        "stato VARCHAR(20) NOT NULL DEFAULT 'pending',"
        "payload TEXT NOT NULL,"
        "creato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
        "stampato_il TIMESTAMP NULL,"
        "CONSTRAINT fk_printjobs_tenant FOREIGN KEY (tenant_id) REFERENCES tenant(id),"
        "CONSTRAINT fk_printjobs_dispositivo FOREIGN KEY (dispositivo_id) "
        "REFERENCES dispositivi_stampa(id))"
    )


def bootstrap():
    """Crea le tabelle multi-tenant se non esistono e un admin di test."""
    print(f"\n{YELLOW}== Bootstrap DB multi-tenant =={RES}")
    with connection() as conn:
        c = conn.cursor()
        _crea_tabelle(c)
        conn.commit()

    # Crea tenant e admin di test (idempotente).
    email = "admin@test.local"
    existing = tenant_repo.trova_utente_by_email(email)
    if existing:
        print(f"  {YELLOW}INFO{RES}  utente di test gia' presente (tenant {existing['tenant_id']})")
        return existing["tenant_id"]

    tid = tenant_repo.crea_tenant("Laboratorio Test", "basic")
    tenant_repo.crea_utente(tid, email, auth.hash_password("Prova123!"), "admin")
    print(f"  {GREEN}OK{RES}  tenant {tid} + admin creati")
    return tid


# ------------------------------------------------------------------------- #
#  Test
# ------------------------------------------------------------------------- #
def test_auth_logic(tenant_id):
    print(f"\n{YELLOW}== Auth (JWT + bcrypt) =={RES}")
    token = auth.create_token("admin@test.local", tenant_id, "admin", "access")
    info = auth.decode_token(token)
    check(info["tenant_id"] == tenant_id, "tenant_id nel JWT")
    check(info["ruolo"] == "admin", "ruolo nel JWT")
    check(auth.verify_password("Prova123!", auth.hash_password("Prova123!")), "bcrypt round-trip")
    check(not auth.verify_password("sbagliata", auth.hash_password("Prova123!")), "bcrypt rifiuta pw errata")


def test_stampa_e_barcode():
    print(f"\n{YELLOW}== Stampa (DDT/scontrino/etichetta) + barcode =={RES}")
    pdf = printing.genera_ddt_pdf(
        numero=1, data="01/01/24", fornitore="Fornitore Test",
        righe=[{"taglio": "Bovino", "peso": "10", "merceologia": "Secondi"}],
    )
    check(pdf.startswith(b"%PDF"), f"DDT PDF generato ({len(pdf)} bytes)")

    esc = printing.genera_scontrino_escpos(
        testata="Bar Test",
        righe=[{"desc": "Prodotto", "prezzo": "5.00"}, {"desc": "Altro", "prezzo": "3.00"}],
        totale="8.00", iva="22%",
    )
    check(isinstance(esc, bytes) and len(esc) > 0, f"Scontrino ESC/POS ({len(esc)} bytes)")

    et = printing.genera_etichetta_dymo_pdf(
        plu="0001", prodotto="Bovino", prezzo_kg="12.50", ingredienti=["x"], codice="123",
    )
    check(et.startswith(b"%PDF"), f"Etichetta DYMO PDF ({len(et)} bytes)")

    check(barcode.valida_ean13("8001234567897"), "EAN-13 valido accettato")
    check(not barcode.valida_ean13("123"), "EAN-13 non valido rifiutato")


def test_print_job_flow(tenant_id):
    print(f"\n{YELLOW}== Coda di stampa + Local Print Agent flow =={RES}")
    # Registra un dispositivo (agent).
    token = "tok_" + ("x" * 32)
    did = print_repo.registra_dispositivo(tenant_id, "Pdv 1", token, "DYMO LabelWriter 450 Turbo")
    check(did is not None and did > 0, f"dispositivo registrato (id={did})")

    disp = print_repo.trova_dispositivo_by_token(token)
    check(disp is not None and disp["tenant_id"] == tenant_id, "trova dispositivo per token")

    # Accoda un job.
    job_id = print_repo.accoda_job(tenant_id, None, "etichetta", '{"plu":"0001"}')
    check(job_id > 0, f"job accodato (id={job_id})")

    # L'agent preleva il prossimo job pending.
    job = print_repo.prendi_prossimo_job(did)
    check(job is not None and job["id"] == job_id, "agent preleva il job pending (stato->printing)")

    # L'agent segnala stampa completata.
    print_repo.aggiorna_stato_job(job_id, "done")
    jobs = print_repo.elenca_job(tenant_id, stato="done")
    check(any(j["id"] == job_id and j["stato"] == "done" for j in jobs), "job in stato 'done'")

    # Nessun altro job pending.
    check(print_repo.prendi_prossimo_job(did) is None, "coda vuota dopo il completamento")


def test_reparti_service(tenant_id):
    print(f"\n{YELLOW}== Reparti service =={RES}")
    nuovo = reparti_service.crea_reparto("Cucina", 1, 0, tenant_id)
    check(nuovo is not None and nuovo.reparto == "Cucina", "creazione reparto in tenant")

    trovato = reparti_service.trova_reparto(nuovo.id, tenant_id)
    check(trovato is not None and trovato.id == nuovo.id, "ricerca reparto per id")

    reparti = reparti_service.lista_reparti(tenant_id)
    check(any(r.id == nuovo.id for r in reparti), "lista reparti del tenant")

    reparti_service.aggiorna_reparto(trovato, "Cucina 2", 1, 1, tenant_id)
    aggiornato = reparti_service.trova_reparto(nuovo.id, tenant_id)
    check(aggiornato is not None and aggiornato.reparto == "Cucina 2", "aggiornamento reparto")

    reparti_service.elimina_reparto(aggiornato, tenant_id)
    check(reparti_service.trova_reparto(nuovo.id, tenant_id) is None, "eliminazione reparto")


def test_fornitori_service(tenant_id):
    print(f"\n{YELLOW}== Fornitori service =={RES}")
    nuovo = fornitori_service.crea_fornitore("Acme Srl", 1, 0, tenant_id)
    check(nuovo is not None and nuovo.azienda == "Acme Srl", "creazione fornitore in tenant")

    trovato = fornitori_service.trova_fornitore(nuovo.id, tenant_id)
    check(trovato is not None and trovato.id == nuovo.id, "ricerca fornitore per id")

    fornitori = fornitori_service.lista_fornitori(tenant_id)
    check(any(f.id == nuovo.id for f in fornitori), "lista fornitori del tenant")

    fornitori_service.aggiorna_fornitore(trovato, "Acme 2", 1, 1, tenant_id)
    aggiornato = fornitori_service.trova_fornitore(nuovo.id, tenant_id)
    check(aggiornato is not None and aggiornato.azienda == "Acme 2", "aggiornamento fornitore")

    fornitori_service.elimina_fornitore(aggiornato, tenant_id)
    check(fornitori_service.trova_fornitore(nuovo.id, tenant_id) is None, "eliminazione fornitore")


def test_tagli_service(tenant_id):
    print(f"\n{YELLOW}== Tagli service =={RES}")
    nuovo = tagli_service.crea_taglio("Bovino", 1, tenant_id)
    check(nuovo is not None and nuovo.taglio == "Bovino", "creazione taglio in tenant")

    trovato = tagli_service.trova_taglio(nuovo.id, tenant_id)
    check(trovato is not None and trovato.id == nuovo.id, "ricerca taglio per id")

    tagli = tagli_service.lista_tagli(tenant_id)
    check(any(t.id == nuovo.id for t in tagli), "lista tagli del tenant")

    tagli_service.aggiorna_taglio(trovato, "Bovino 2", 1, tenant_id)
    aggiornato = tagli_service.trova_taglio(nuovo.id, tenant_id)
    check(aggiornato is not None and aggiornato.taglio == "Bovino 2", "aggiornamento taglio")

    tagli_service.elimina_taglio(aggiornato, tenant_id)
    check(tagli_service.trova_taglio(nuovo.id, tenant_id) is None, "eliminazione taglio")


def main():
    print(f"{YELLOW}=== Test end-to-end SaaS GestLab (S14) ==={RES}")
    tenant_id = bootstrap()
    test_auth_logic(tenant_id)
    test_stampa_e_barcode()
    test_print_job_flow(tenant_id)
    test_reparti_service(tenant_id)
    test_fornitori_service(tenant_id)
    test_tagli_service(tenant_id)

    print(f"\n=== Risultato: {GREEN}{_passed} passati{RES}, {RED}{_failed} falliti{RES} ===")
    if _failed:
        print(f"{RED}TEST FALLITI{RES}")
        sys.exit(1)
    print(f"{GREEN}TEST SUPERATI{RES}")


if __name__ == "__main__":
    main()
