"""Accesso al database per l'applicazione GestLab2.

Le credenziali e i parametri di connessione vengono letti da ``config.ini``
(section ``[DataBase]``). La connessione e il cursore sono creati una sola
volta a livello di modulo e riusati dalle varie funzioni di lettura.
"""

import configparser
import os

import mysql.connector


def _leggi_config():
    """Legge la sezione [DataBase] da config.ini nella directory del progetto."""
    config = configparser.ConfigParser()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config.read(os.path.join(base_dir, 'config.ini'))
    return config['DataBase']


_db_config = _leggi_config()

conn = mysql.connector.connect(
    host=_db_config.get('host', 'localhost'),
    port=_db_config.getint('port', 3306),
    database=_db_config.get('db', 'data'),
    user=_db_config.get('user', 'root'),
    password=_db_config.get('pwd', ''),
)

# Cursore condiviso per le query di lettura.
c = conn.cursor()


def _recupera_primi():
    c.execute("SELECT prodotto, plu FROM prodotti WHERE merceologia = 'Primi piatti'")
    return [{'prodotto': str(x[0]), 'plu': str(x[1])} for x in c]


def _recupera_secondi():
    c.execute("SELECT prodotto, plu FROM prodotti WHERE merceologia = 'Secondi piatti'")
    return [{'prodotto': str(x[0]), 'plu': str(x[1])} for x in c]


def _recupera_contorni():
    c.execute("SELECT prodotto, plu FROM prodotti WHERE merceologia = 'Contorni'")
    return [{'prodotto': str(x[0]), 'plu': str(x[1])} for x in c]


def _recupera_progressivo_ingresso():
    c.execute("SELECT prog_acq FROM progressivi")
    return c.fetchone()[0]


def _recupera_lista_fornitori():
    c.execute("SELECT azienda FROM fornitori WHERE flag1_ing_merce = 1")
    fornitori = []
    for lista in c:
        fornitori.extend(lista)
    return fornitori


def _lista_tagli(cat):
    lista = []
    cur = conn.cursor()
    query = 'SELECT taglio FROM tagli WHERE Id_Merceologia=%s'
    cur.execute(query, [cat])
    for x in cur:
        lista.extend(x)
    cur.close()
    return lista


def _recupera_merceologia_da_id(cat):
    c.execute("SELECT merceologia FROM merceologie WHERE Id = %s", [cat])
    return c.fetchone()[0]


def _recupera_lotti_aperti():
    c.execute(
        "SELECT progressivo_acq, fornitore, prodotto, residuo "
        "FROM ingresso_merce WHERE lotto_chiuso = 'no'"
    )
    return [{'number': str(x[0]), 'fornit': str(x[1]),
             'name': str(x[2]), 'peso': str(x[3])} for x in c]


# -------------------------------------------------------------------------------- #
# anag_dipendenti
# -------------------------------------------------------------------------------- #

def _recupera_reparti():
    """Recupera i reparti abilitati per i dipendenti (flag1_dip = 1)."""
    c.execute("SELECT ID, reparto FROM reparti WHERE flag1_dip = 1 ORDER BY ID")
    return [{'id': str(x[0]), 'reparto': str(x[1])} for x in c]

