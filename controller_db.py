import mysql.connector

conn = mysql.connector.connect(host="localhost",
                                   database="data",
                                   user="root",
                                   password='stup3nd0')

c = conn.cursor()


def _recupera_primi():
        c.execute("SELECT prodotto, plu FROM prodotti WHERE merceologia ='Primi piatti'")
        return [{'prodotto': str(x[0]), 'plu': str(x[1])} for x in c]

def _recupera_secondi():
        c.execute("SELECT prodotto, plu FROM prodotti WHERE merceologia ='Secondi piatti'")
        return [{'prodotto': str(x[0]), 'plu': str(x[1])} for x in c]
    
def _recupera_contorni():
    c.execute("SELECT prodotto, plu FROM prodotti WHERE merceologia ='Contorni'")
    return [{'prodotto': str(x[0]), 'plu': str(x[1])} for x in c]

def _recupera_progressivo_ingresso():
        c.execute("SELECT prog_acq FROM progressivi")
        prog_ingresso = c.fetchone()[0]
        return prog_ingresso

def _recupera_lista_fornitori():
        c.execute("SELECT azienda FROM fornitori WHERE flag1_ing_merce = 1")
        fornitori = []
        for lista in c:
            fornitori.extend(lista)
        return fornitori

def _lista_tagli(cat):
       lista = []
       lista.clear()
       c = conn.cursor()
       cat_merc = [cat,]
       query = 'SELECT taglio FROM tagli WHERE Id_Merceologia=%s'
       c.execute(query, cat_merc)
       for x in c:
               lista.extend(x)
       return lista

def _recupera_merceologia_da_id(cat):
        c.execute("SELECT merceologia FROM merceologie WHERE Id = %s", [cat,])
        merc = c.fetchone()[0]
        return merc

def _recupera_lotti_aperti():
        c.execute("SELECT progressivo_acq, fornitore, prodotto, residuo FROM ingresso_merce WHERE lotto_chiuso = 'no'")
        return [{'number': str(x[0]), 'fornit': str(x[1]), 'name':str(x[2]), 'peso':str(x[3])} for x in c]


# ---------------------------------------------------------------- #
# anag_dipendenti
# ---------------------------------------------------------------- #

def _recupera_dipendenti():
        """Recupera tutti i dipendenti dalla tabella dipendenti."""
        c.execute("SELECT ID, nome, email, reparto FROM dipendenti ORDER BY ID")
        return [{'id': str(x[0]), 'nome': str(x[1]), 'email': str(x[2]), 'reparto': x[3]} for x in c]


def _recupera_reparti():
        """Recupera i reparti abilitati per i dipendenti (flag1_dip = 1)."""
        c.execute("SELECT ID, reparto FROM reparti WHERE flag1_dip = 1 ORDER BY ID")
        return [{'id': str(x[0]), 'reparto': str(x[1])} for x in c]


def _inserisci_dipendente(nome, email, reparto):
        """Inserisce un nuovo dipendente e restituisce l'ID generato."""
        c.execute(
            "INSERT INTO dipendenti (nome, email, reparto) VALUES (%s, %s, %s)",
            (nome, email, reparto),
        )
        conn.commit()
        return c.lastrowid


def _modifica_dipendente(id_dip, nome, email, reparto):
        """Aggiorna i dati di un dipendente esistente."""
        c.execute(
            "UPDATE dipendenti SET nome = %s, email = %s, reparto = %s WHERE ID = %s",
            (nome, email, reparto, id_dip),
        )
        conn.commit()


def _elimina_dipendente(id_dip):
        """Elimina un dipendente tramite il suo ID."""
        c.execute("DELETE FROM dipendenti WHERE ID = %s", (id_dip,))
        conn.commit()
