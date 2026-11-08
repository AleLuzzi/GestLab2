"""Bootstrap del DB multi-tenant e dell'utente admin iniziale.

Legge e esegue il file init_database.sql (schema unificato) per creare tutte
le tabelle di business e SaaS. Quindi crea un tenant e un utente admin
iniziali.

Esecuzione:
    python -m saas.bootstrap

Variabili d'ambiente (opzionali, per sovrascrivere le credenziali di default):
    GESTLAB_ADMIN_EMAIL     (default: admin@gestlab.it)
    GESTLAB_ADMIN_PASSWORD  (default: Admin123!)
    GESTLAB_TENANT_NOME     (default: Laboratorio Principale)
"""

import os
import re
import sys

# Assicura che il progetto sia nel path (se eseguito da altrove).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import connection
from saas import auth
from saas.repositories import tenant_repo

# Credenziali admin di default (sovrascrivibili via env).
ADMIN_EMAIL = os.environ.get("GESTLAB_ADMIN_EMAIL", "admin@gestlab.it")
ADMIN_PASSWORD = os.environ.get("GESTLAB_ADMIN_PASSWORD", "Admin123!")
TENANT_NOME = os.environ.get("GESTLAB_TENANT_NOME", "Laboratorio Principale")

# Percorso del file SQL unificato.
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "init_database.sql")
MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")
MIGRATION_ORDER = (
    "20261003_stock_traceability.sql",
    "20261031_articoli_input_lavorazione.sql",
    "20261031_lotti_data_index.sql",
    "20261031_soggetti_clienti_fornitori.sql",
    "20261031_work_operator_id.sql",
    "20261107_lotti_metadata.sql",
    "20261107_lotti_tmc.sql",
    "20261107_note_lotto.sql",
    "20261107_movimenti_lotto_vendita.sql",
    "20261108_ricette.sql",
    "20261108_ricetta_ingredienti.sql",
    "20261108_ricetta_allergeni_durata.sql",
    "20261108_lavorazioni_ricetta.sql",
    "20261108_dati_osa_tenant.sql",
    "20261108_motivo_rettifica_lotto.sql",
    "20261108_vendite.sql",
)


def _remove_sql_comments(sql_line):
    """Rimuove commenti SQL da una riga."""
    # Rimuove commenti -- (SQL standard)
    idx = sql_line.find("--")
    if idx != -1:
        sql_line = sql_line[:idx]
    return sql_line.strip()


def _parse_sql_statements(sql_content):
    """Parsifica il file SQL rimuovendo commenti e dividendo gli statement.
    
    Args:
        sql_content: contenuto grezzo del file SQL
        
    Returns:
        list: lista di statement SQL validi (non vuoti, senza commenti)
    """
    statements = []
    current_stmt = []
    
    for line in sql_content.split("\n"):
        # Rimuove commenti da questa riga
        clean_line = _remove_sql_comments(line)
        if not clean_line:
            continue
        
        current_stmt.append(clean_line)
        
        # Se la riga termina con ;, abbiamo uno statement completo
        if clean_line.endswith(";"):
            stmt = " ".join(current_stmt)
            # Rimuove il ; finale e il whitespace
            stmt = stmt.rstrip(";").strip()
            if stmt:
                statements.append(stmt)
            current_stmt = []
    
    # Aggiunge l'ultimo statement se c'è
    if current_stmt:
        stmt = " ".join(current_stmt).rstrip(";").strip()
        if stmt:
            statements.append(stmt)
    
    return statements


def _schema_richiesto():
    """Restituisce le colonne e le chiavi primarie previste dallo schema."""
    with open(SCHEMA_FILE, "r", encoding="utf-8") as file_schema:
        sql_content = file_schema.read()

    tables = {}
    pattern = re.compile(
        r"CREATE TABLE IF NOT EXISTS `([^`]+)`\s*\((.*?)\)\s*ENGINE=",
        re.DOTALL,
    )
    for match in pattern.finditer(sql_content):
        table_name, definition = match.groups()
        columns = set(
            re.findall(r"(?m)^\s*`([^`]+)`\s+[a-zA-Z]", definition)
        )
        primary_key = re.search(r"PRIMARY KEY\s*\(([^)]+)\)", definition)
        if not columns or primary_key is None:
            raise ValueError(
                f"Definizione incompleta nello schema per la tabella {table_name}"
            )
        tables[table_name] = columns

    if not tables:
        raise ValueError(f"Nessuna tabella trovata nello schema {SCHEMA_FILE}")
    return tables


def _verifica_schema(cursor):
    """Interrompe il bootstrap se lo schema DB non soddisfa il contratto corrente."""
    richiesto = _schema_richiesto()
    cursor.execute(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = DATABASE()"
    )
    colonne_db = {}
    for table_name, column_name in cursor.fetchall():
        colonne_db.setdefault(table_name, set()).add(column_name)

    cursor.execute(
        "SELECT table_name FROM information_schema.key_column_usage "
        "WHERE table_schema = DATABASE() AND constraint_name = 'PRIMARY'"
    )
    tabelle_con_pk = {row[0] for row in cursor.fetchall()}

    errori = []
    for table_name, colonne_richieste in richiesto.items():
        colonne_mancanti = colonne_richieste - colonne_db.get(table_name, set())
        if table_name not in colonne_db:
            errori.append(f"{table_name}: tabella assente")
        elif colonne_mancanti:
            errori.append(
                f"{table_name}: colonne mancanti "
                f"{', '.join(sorted(colonne_mancanti))}"
            )
        if table_name not in tabelle_con_pk:
            errori.append(f"{table_name}: chiave primaria assente")

    if errori:
        dettagli = "; ".join(errori)
        raise RuntimeError(f"Schema database non allineato: {dettagli}")


def _migra_progressivi_tenant(cursor):
    """Consolida i progressivi tenant e garantisce un solo record per tenant."""
    cursor.execute(
        "SELECT COUNT(*) FROM progressivi WHERE tenant_id IS NULL"
    )
    righe_senza_tenant = cursor.fetchone()[0]
    if righe_senza_tenant:
        raise RuntimeError(
            "Impossibile aggiungere la chiave primaria a progressivi: "
            f"{righe_senza_tenant} record senza tenant_id richiedono "
            "riconciliazione manuale."
        )

    cursor.execute(
        "SELECT tenant_id, MAX(prog_acq), MAX(prog_ven), COUNT(*) "
        "FROM progressivi WHERE tenant_id IS NOT NULL "
        "GROUP BY tenant_id HAVING COUNT(*) > 1"
    )
    duplicati = cursor.fetchall()

    for tenant_id, prog_acq, prog_ven, numero_record in duplicati:
        cursor.execute(
            "UPDATE progressivi SET prog_acq = %s, prog_ven = %s "
            "WHERE tenant_id = %s",
            (prog_acq, prog_ven, tenant_id),
        )
        cursor.execute(
            "DELETE FROM progressivi WHERE tenant_id = %s LIMIT %s",
            (tenant_id, numero_record - 1),
        )
        if cursor.rowcount != numero_record - 1:
            raise RuntimeError(
                f"Impossibile consolidare i progressivi del tenant {tenant_id}"
            )

    cursor.execute("SHOW INDEX FROM progressivi")
    indici = cursor.fetchall()
    indici_tenant_univoci = {}
    for indice in indici:
        nome = indice[2]
        non_univoco = indice[1]
        posizione = indice[3]
        colonna = indice[4]
        if not non_univoco:
            indici_tenant_univoci.setdefault(nome, []).append((posizione, colonna))

    indice_presente = any(
        colonne == [(1, "tenant_id")]
        for colonne in indici_tenant_univoci.values()
    )
    if not indice_presente:
        cursor.execute(
            "ALTER TABLE progressivi "
            "ADD UNIQUE KEY uq_progressivi_tenant_id (tenant_id)"
        )

    chiavi_primarie = {}
    for indice in indici:
        if indice[2] == "PRIMARY":
            chiavi_primarie.setdefault(indice[2], []).append((indice[3], indice[4]))
    colonne_pk = next(iter(chiavi_primarie.values()), [])
    if colonne_pk and colonne_pk != [(1, "tenant_id")]:
        raise RuntimeError(
            "La chiave primaria di progressivi non coincide con tenant_id"
        )
    if not colonne_pk:
        cursor.execute(
            "ALTER TABLE progressivi "
            "MODIFY COLUMN tenant_id bigint NOT NULL, "
            "ADD PRIMARY KEY (tenant_id)"
        )


def _migra_catalogo_articoli(cursor):
    """Aggiunge i campi condivisi del catalogo agli schemi già inizializzati."""
    cursor.execute("SHOW COLUMNS FROM articoli")
    colonne = {riga[0] for riga in cursor.fetchall()}
    if "ean" not in colonne:
        cursor.execute("ALTER TABLE articoli ADD COLUMN ean varchar(32) DEFAULT NULL")
    if "prezzo_unitario" not in colonne:
        cursor.execute(
            "ALTER TABLE articoli "
            "ADD COLUMN prezzo_unitario decimal(12,2) DEFAULT NULL"
        )

    cursor.execute("SHOW INDEX FROM articoli")
    indici_ean = {
        riga[2]
        for riga in cursor.fetchall()
        if riga[4] == "ean" and riga[1] == 0
    }
    if "uq_articoli_tenant_ean" not in indici_ean:
        cursor.execute(
            "ALTER TABLE articoli "
            "ADD UNIQUE KEY uq_articoli_tenant_ean (tenant_id, ean)"
        )


def _archivia_ingresso_merce_legacy(cursor):
    """Rinomina la tabella legacy preservandone schema e dati."""
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = DATABASE() AND table_name = %s",
        ("ingresso_merce",),
    )
    tabella_legacy_esiste = cursor.fetchone()[0] > 0

    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = DATABASE() AND table_name = %s",
        ("ingresso_merce_legacy_archive",),
    )
    archivio_esiste = cursor.fetchone()[0] > 0

    if tabella_legacy_esiste and archivio_esiste:
        raise RuntimeError(
            "Esistono sia ingresso_merce sia ingresso_merce_legacy_archive; "
            "verificare e riconciliare manualmente le due tabelle prima del bootstrap."
        )
    if tabella_legacy_esiste:
        cursor.execute(
            "RENAME TABLE `ingresso_merce` TO `ingresso_merce_legacy_archive`"
        )
        return True
    return False


def _database_contiene_tabelle(cursor):
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'"
    )
    return cursor.fetchone()[0] > 0


def _colonne_tabella(cursor, tabella):
    cursor.execute(f"SHOW COLUMNS FROM `{tabella}`")
    return {riga[0] for riga in cursor.fetchall()}


def _indici_tabella(cursor, tabella):
    cursor.execute(f"SHOW INDEX FROM `{tabella}`")
    return {riga[2] for riga in cursor.fetchall()}


def _tabella_esiste(cursor, tabella):
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = DATABASE() AND table_name = %s",
        (tabella,),
    )
    return cursor.fetchone()[0] > 0


def _migrazione_gia_applicata(cursor, migrazione):
    """Riconosce gli aggiornamenti eseguiti prima dell'introduzione del registro."""
    if migrazione == "20261003_stock_traceability.sql":
        tabelle = (
            "articoli",
            "documenti_ingresso",
            "lavorazioni",
            "lotti",
            "movimenti_lotto",
            "lavorazione_scarto",
            "righe_ingresso_tracciato",
            "lavorazione_input",
            "lavorazione_output",
        )
        return all(_tabella_esiste(cursor, tabella) for tabella in tabelle)

    if migrazione == "20261031_articoli_input_lavorazione.sql":
        return "utilizzabile_come_input" in _colonne_tabella(cursor, "articoli")

    if migrazione == "20261031_lotti_data_index.sql":
        return "idx_lotti_tenant_data" in _indici_tabella(cursor, "lotti")

    if migrazione == "20261031_soggetti_clienti_fornitori.sql":
        return (
            _tabella_esiste(cursor, "soggetti")
            and _tabella_esiste(cursor, "soggetti_ruoli")
            and "soggetto_id" in _colonne_tabella(cursor, "fornitori")
            and "fornitore_id" in _colonne_tabella(cursor, "documenti_ingresso")
        )

    if migrazione == "20261031_work_operator_id.sql":
        return (
            "operatore_id" in _colonne_tabella(cursor, "lavorazioni")
            and "idx_lavorazioni_operatore" in _indici_tabella(cursor, "lavorazioni")
        )

    if migrazione == "20261107_lotti_metadata.sql":
        colonne = _colonne_tabella(cursor, "lotti")
        return {
            "data_scadenza",
            "lotto_fornitore",
            "origine",
            "temperatura_ingresso",
        }.issubset(colonne)

    if migrazione == "20261107_lotti_tmc.sql":
        if "data_tmc" not in _colonne_tabella(cursor, "lotti"):
            return False
        cursor.execute("SHOW CREATE TABLE `lotti`")
        schema = cursor.fetchone()[1]
        return "CHK_LOTTI_DATA_SCADENZA_TMC" in schema.upper()

    if migrazione == "20261107_note_lotto.sql":
        return "note_lotto" in _colonne_tabella(cursor, "lotti")

    if migrazione == "20261107_movimenti_lotto_vendita.sql":
        cursor.execute("SHOW CREATE TABLE `movimenti_lotto`")
        schema = cursor.fetchone()[1]
        return (
            "VENDITA" in schema.upper()
            and "CHK_MOVIMENTI_LOTTO_TIPO" in schema.upper()
        )

    if migrazione == "20261108_ricette.sql":
        if not _tabella_esiste(cursor, "ricette"):
            return False
        colonne = _colonne_tabella(cursor, "ricette")
        if not {
            "tenant_id",
            "nome",
            "articolo_id",
            "resa_attesa",
            "scarto_atteso",
            "attiva",
        }.issubset(colonne):
            return False
        cursor.execute("SHOW CREATE TABLE `ricette`")
        schema = cursor.fetchone()[1].upper()
        return "FK_RICETTE_ARTICOLO" in schema and "CHK_RICETTE_QUANTITA" in schema

    if migrazione == "20261108_ricetta_ingredienti.sql":
        if not _tabella_esiste(cursor, "ricetta_ingredienti"):
            return False
        colonne = _colonne_tabella(cursor, "ricetta_ingredienti")
        if not {
            "tenant_id",
            "ricetta_id",
            "articolo_id",
            "posizione",
            "tipo_quantita",
            "valore",
            "obbligatorio",
        }.issubset(colonne):
            return False
        cursor.execute("SHOW CREATE TABLE `ricetta_ingredienti`")
        schema = cursor.fetchone()[1].upper()
        return (
            "FK_RICETTA_INGREDIENTI_RICETTA" in schema
            and "FK_RICETTA_INGREDIENTI_ARTICOLO" in schema
            and "CHK_RICETTA_INGREDIENTI_QUANTITA" in schema
        )

    if migrazione == "20261108_ricetta_allergeni_durata.sql":
        if not _tabella_esiste(cursor, "ricette") or not _tabella_esiste(
            cursor, "ricetta_allergeni"
        ):
            return False
        colonne_ricette = _colonne_tabella(cursor, "ricette")
        if not {
            "giorni_vita",
            "istruzioni_conservazione",
            "istruzioni_cottura",
        }.issubset(colonne_ricette):
            return False
        colonne_allergeni = _colonne_tabella(cursor, "ricetta_allergeni")
        if not {"tenant_id", "ricetta_id", "codice"}.issubset(colonne_allergeni):
            return False
        cursor.execute("SHOW CREATE TABLE `ricetta_allergeni`")
        schema_allergeni = cursor.fetchone()[1].upper()
        cursor.execute("SHOW CREATE TABLE `ricette`")
        schema_ricette = cursor.fetchone()[1].upper()
        return (
            "FK_RICETTA_ALLERGENI_RICETTA" in schema_allergeni
            and "CHK_RICETTA_ALLERGENI_CODICE" in schema_allergeni
            and "CHK_RICETTE_GIORNI_VITA" in schema_ricette
        )

    if migrazione == "20261108_lavorazioni_ricetta.sql":
        if "ricetta_id" not in _colonne_tabella(cursor, "lavorazioni"):
            return False
        cursor.execute("SHOW CREATE TABLE `lavorazioni`")
        schema = cursor.fetchone()[1].upper()
        return (
            "FK_LAVORAZIONI_RICETTA" in schema
            and "IDX_LAVORAZIONI_RICETTA" in schema
        )

    if migrazione == "20261108_dati_osa_tenant.sql":
        return {
            "osa_ragione_sociale",
            "osa_indirizzo",
            "osa_laboratorio",
            "osa_partita_iva",
        }.issubset(_colonne_tabella(cursor, "tenant"))

    if migrazione == "20261108_motivo_rettifica_lotto.sql":
        return "motivo" in _colonne_tabella(cursor, "movimenti_lotto")

    if migrazione == "20261108_vendite.sql":
        colonne_vendite = {
            "tenant_id",
            "numero",
            "data_vendita",
            "cliente_id",
            "tipo_documento",
        }
        colonne_righe = {
            "tenant_id",
            "vendita_id",
            "lotto_id",
            "articolo_id",
            "quantita",
            "unita_misura",
            "prezzo_unitario",
            "iva_percentuale",
        }
        if not (
            _tabella_esiste(cursor, "vendite")
            and _tabella_esiste(cursor, "righe_vendita")
            and colonne_vendite.issubset(_colonne_tabella(cursor, "vendite"))
            and colonne_righe.issubset(_colonne_tabella(cursor, "righe_vendita"))
        ):
            return False

        cursor.execute("SHOW CREATE TABLE `vendite`")
        schema_vendite = cursor.fetchone()[1].upper()
        cursor.execute("SHOW CREATE TABLE `righe_vendita`")
        schema_righe = cursor.fetchone()[1].upper()
        return all(
            vincolo in schema_vendite
            for vincolo in (
                "PRIMARY KEY (`ID`)",
                "UQ_VENDITE_TENANT_ID",
                "UQ_VENDITE_TENANT_NUMERO",
                "CHK_VENDITE_TIPO_DOCUMENTO",
                "FK_VENDITE_TENANT",
                "FK_VENDITE_CLIENTE",
            )
        ) and all(
            vincolo in schema_righe
            for vincolo in (
                "PRIMARY KEY (`ID`)",
                "CHK_RIGHE_VENDITA_QUANTITA_PREZZO_IVA",
                "FK_RIGHE_VENDITA_DOCUMENTO",
                "FK_RIGHE_VENDITA_LOTTO",
                "FK_RIGHE_VENDITA_ARTICOLO",
            )
        )

    raise ValueError(f"Migrazione non registrata: {migrazione}")


def _registra_migrazione(cursor, migrazione):
    cursor.execute(
        "INSERT INTO `schema_migrations` (`migration_id`) VALUES (%s)",
        (migrazione,),
    )


def _applica_migrazioni(cursor, commit, database_nuovo=False):
    """Applica o registra tutte le migrazioni nell'ordine canonico."""
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS `schema_migrations` ("
        "`migration_id` varchar(255) NOT NULL, "
        "`applied_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP, "
        "PRIMARY KEY (`migration_id`)"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    )
    cursor.execute("SELECT `migration_id` FROM `schema_migrations`")
    applicate = {riga[0] for riga in cursor.fetchall()}

    for migrazione in MIGRATION_ORDER:
        if migrazione in applicate:
            continue

        percorso = os.path.join(MIGRATIONS_DIR, migrazione)
        if not os.path.isfile(percorso):
            raise FileNotFoundError(f"File di migrazione non trovato: {percorso}")

        if database_nuovo or _migrazione_gia_applicata(cursor, migrazione):
            _registra_migrazione(cursor, migrazione)
            commit()
            print(f"  OK  migrazione gia' presente: {migrazione}")
            continue

        with open(percorso, "r", encoding="utf-8") as file_migrazione:
            statements = _parse_sql_statements(file_migrazione.read())
        if not statements:
            raise ValueError(f"Nessuno statement nella migrazione: {percorso}")
        for statement in statements:
            cursor.execute(statement)

        _registra_migrazione(cursor, migrazione)
        commit()
        print(f"  OK  migrazione applicata: {migrazione}")


def crea_tabelle():
    """Esegue init_database.sql per creare tutte le tabelle (idempotente)."""
    if not os.path.exists(SCHEMA_FILE):
        raise FileNotFoundError(f"Schema file non trovato: {SCHEMA_FILE}")

    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Parsifica gli statement rimuovendo commenti
    statements = _parse_sql_statements(sql_content)
    
    if not statements:
        raise ValueError(f"Nessuno statement SQL trovato in {SCHEMA_FILE}")
    
    print(f"  Info: trovati {len(statements)} statement da eseguire")

    with connection() as conn:
        c = conn.cursor()
        database_nuovo = not _database_contiene_tabelle(c)
        if _archivia_ingresso_merce_legacy(c):
            print("  OK  ingresso_merce archiviata come ingresso_merce_legacy_archive")
        executed = 0
        
        for i, stmt in enumerate(statements, 1):
            c.execute(stmt)
            executed += 1

        _migra_progressivi_tenant(c)
        _migra_catalogo_articoli(c)
        conn.commit()
        _applica_migrazioni(c, conn.commit, database_nuovo)
        _verifica_schema(c)
    
    print(f"  OK  schema eseguito: {executed}/{len(statements)} statement completati")


def crea_admin():
    """Crea tenant + admin iniziale se non esistono (idempotente)."""
    existing = tenant_repo.trova_utente_by_email(ADMIN_EMAIL)
    if existing:
        print(f"  OK  utente admin gia' presente (tenant {existing['tenant_id']})")
        return existing["tenant_id"]

    tid = tenant_repo.crea_tenant(TENANT_NOME, "basic")
    tenant_repo.crea_utente(tid, ADMIN_EMAIL, auth.hash_password(ADMIN_PASSWORD), "admin")
    print(f"  OK  tenant '{TENANT_NOME}' (id={tid}) creato")
    print(f"  OK  admin '{ADMIN_EMAIL}' creato")
    return tid


def main():
    print("=== Bootstrap GestLab SaaS ===\n")
    print(f"1. Creazione schema da: {SCHEMA_FILE}")
    crea_tabelle()
    print(f"\n2. Creazione tenant e admin iniziale")
    tid = crea_admin()
    print(f"\n✓ Setup completato!\n")
    print(f"Credenziali di accesso alla console web:")
    print(f"  URL:      http://localhost:8000/")
    print(f"  Email:    {ADMIN_EMAIL}")
    print(f"  Password: {ADMIN_PASSWORD}")
    print(f"  Ruolo:    admin")
    print(f"\nAvvia il server con:")
    print(f"  python -m uvicorn saas.main:app --reload")


if __name__ == "__main__":
    main()
