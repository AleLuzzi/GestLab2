"""Modelli Record per le entita' del dominio (framework-agnostici).

Portati in ``core`` dal progetto ``Laboratorio`` per unificare il data layer.
Ogni modello e' una classe "Record" con metodi di accesso al DB che ricevono
``cursor`` e ``conn`` (pattern usato da Laboratorio). Per il SaaS questi
diventeranno i modelli su cui aggiungere il ``tenant_id``.
"""


class Dipendente:
    """Record dipendente (tabella `dipendenti`, campi: id, nome, email, reparto).

    `reparto_nome` e' il nome del reparto risolto tramite JOIN con `reparti`
    (non persistito su `dipendenti`, solo per la visualizzazione).
    """

    __slots__ = ("id", "nome", "email", "reparto", "reparto_nome")

    def __init__(self, id=None, nome="", email="", reparto=None, reparto_nome=None):
        self.id = id
        self.nome = nome
        self.email = email
        self.reparto = reparto
        self.reparto_nome = reparto_nome

    @classmethod
    def from_row(cls, row):
        """Costruisce un oggetto da una riga del DB.

        Supporta righe con:
        - (id, nome)
        - (id, nome, email)
        - (id, nome, email, reparto)
        - (id, nome, email, reparto, reparto_nome)
        """
        if len(row) == 2:
            return cls(row[0], row[1], "", None)
        if len(row) == 3:
            return cls(row[0], row[1], row[2], None)
        if len(row) == 4:
            return cls(row[0], row[1], row[2], row[3])
        return cls(row[0], row[1], row[2], row[3], row[4])

    def params_insert(self):
        """Valori per INSERT INTO dipendenti (nome, email, reparto)."""
        return (self.nome, self.email, self.reparto)

    def params_update(self):
        """Valori per UPDATE dipendenti SET nome=%s, email=%s, reparto=%s WHERE id=%s."""
        return (self.nome, self.email, self.reparto, self.id)

    @classmethod
    def fetch_all(cls, cursor):
        """Recupera tutti i dipendenti presenti nel database."""
        cursor.execute("SELECT id, nome, email, reparto FROM dipendenti")
        return [cls.from_row(row) for row in cursor.fetchall()]

    @classmethod
    def find_by_id(cls, cursor, f_id):
        """Cerca un singolo dipendente tramite il suo ID."""
        cursor.execute("SELECT id, nome, email, reparto FROM dipendenti WHERE id = %s", (f_id,))
        row = cursor.fetchone()
        return cls.from_row(row) if row else None

    def save(self, cursor, conn):
        """Esegue l'aggiornamento (UPDATE) del record corrente."""
        cursor.execute(
            "UPDATE dipendenti SET nome = %s, email = %s, reparto = %s WHERE id = %s",
            self.params_update(),
        )
        conn.commit()

    def delete(self, cursor, conn):
        """Elimina il record corrente dal database."""
        if self.id is None:
            raise ValueError("Impossibile eliminare un dipendente privo di ID.")
        try:
            cursor.execute("DELETE FROM dipendenti WHERE id = %s", (self.id,))
            conn.commit()
            self.id = None
        except Exception as e:
            conn.rollback()
            raise e

    def insert(self, cursor, conn):
        """Esegue l'inserimento (INSERT) del nuovo dipendente."""
        try:
            cursor.execute(
                "INSERT INTO dipendenti (nome, email, reparto) VALUES (%s, %s, %s)",
                self.params_insert(),
            )
            if hasattr(cursor, "lastrowid") and cursor.lastrowid:
                self.id = cursor.lastrowid
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e


class Fornitore:
    """Record fornitore (tabella `fornitori`)."""

    __slots__ = ("id", "azienda", "flag1_ing_merce", "flag2_inventario")

    def __init__(self, id=None, azienda="", flag1_ing_merce=0, flag2_inventario=0):
        self.id = id
        self.azienda = azienda
        self.flag1_ing_merce = int(flag1_ing_merce)
        self.flag2_inventario = int(flag2_inventario)

    @classmethod
    def from_row(cls, row):
        """Costruisce da una riga `SELECT * FROM fornitori`."""
        return cls(row[0], row[1], row[2], row[3])

    def params_insert(self):
        """Valori per INSERT INTO fornitori(azienda, flag1_ing_merce, flag2_inventario)."""
        return (self.azienda, self.flag1_ing_merce, self.flag2_inventario)

    def params_update(self):
        """Valori per UPDATE ... WHERE ID = %s."""
        return (self.azienda, self.flag1_ing_merce, self.flag2_inventario, self.id)

    @classmethod
    def fetch_all(cls, cursor):
        """Recupera tutti i fornitori."""
        cursor.execute("SELECT id, azienda, flag1_ing_merce, flag2_inventario FROM fornitori")
        return [cls.from_row(row) for row in cursor.fetchall()]

    @classmethod
    def find_by_id(cls, cursor, f_id):
        """Cerca un fornitore tramite ID."""
        cursor.execute("SELECT id, azienda, flag1_ing_merce, flag2_inventario FROM fornitori WHERE id = %s", (f_id,))
        row = cursor.fetchone()
        return cls.from_row(row) if row else None

    def save(self, cursor, conn):
        """Esegue l'aggiornamento del record."""
        cursor.execute(
            "UPDATE fornitori SET azienda = %s, flag1_ing_merce = %s, flag2_inventario = %s WHERE id = %s",
            self.params_update(),
        )
        conn.commit()

    def delete(self, cursor, conn):
        """Elimina il record."""
        cursor.execute("DELETE FROM fornitori WHERE id = %s", (self.id,))
        conn.commit()

    def insert(self, cursor, conn):
        """Inserisce il record."""
        cursor.execute(
            "INSERT INTO fornitori(azienda, flag1_ing_merce, flag2_inventario) VALUES (%s, %s, %s)",
            self.params_insert(),
        )
        conn.commit()


class Taglio:
    """Record taglio (tabella `tagli`)."""

    __slots__ = ("id", "taglio", "id_merceologia")

    def __init__(self, id=None, taglio="", id_merceologia=None):
        self.id = id
        self.taglio = taglio or ""
        self.id_merceologia = id_merceologia

    @classmethod
    def from_row(cls, row):
        """Costruisce da una riga `SELECT id, taglio, id_merceologia FROM tagli`."""
        return cls(row[0], row[1], row[2])

    def params_insert(self):
        """Valori per INSERT INTO tagli(taglio, Id_Merceologia)."""
        return (self.taglio, self.id_merceologia)

    def params_update(self):
        """Valori per UPDATE tagli SET taglio=%s, id_merceologia=%s WHERE id=%s."""
        return (self.taglio, self.id_merceologia, self.id)

    @classmethod
    def fetch_all(cls, cursor):
        """Recupera tutti i tagli."""
        cursor.execute("SELECT id, taglio, id_merceologia FROM tagli")
        return [cls.from_row(row) for row in cursor.fetchall()]

    @classmethod
    def find_by_id(cls, cursor, t_id):
        """Cerca un taglio tramite ID."""
        cursor.execute("SELECT id, taglio, id_merceologia FROM tagli WHERE id = %s", (t_id,))
        row = cursor.fetchone()
        return cls.from_row(row) if row else None

    @classmethod
    def find_by_merceologia(cls, cursor, merceologia_id):
        """Recupera tutti i tagli di una merceologia."""
        cursor.execute(
            "SELECT id, taglio, id_merceologia FROM tagli WHERE id_merceologia = %s",
            (merceologia_id,),
        )
        return [cls.from_row(row) for row in cursor.fetchall()]

    def save(self, cursor, conn):
        """Salva il record."""
        cursor.execute(
            "UPDATE tagli SET taglio = %s, id_merceologia = %s WHERE id = %s",
            self.params_update(),
        )
        conn.commit()

    def delete(self, cursor, conn):
        """Elimina il record."""
        cursor.execute("DELETE FROM tagli WHERE id = %s", (self.id,))
        conn.commit()

    def insert(self, cursor, conn):
        """Inserisce il record."""
        cursor.execute(
            "INSERT INTO tagli(taglio, Id_Merceologia) VALUES (%s, %s)",
            self.params_insert(),
        )
        conn.commit()


class Merceologia:
    """Record merceologia (tabella `merceologie`).

    `reparto_nome` e' il nome del reparto risolto tramite JOIN con `reparti`
    (non persistito sulla tabella, solo per la visualizzazione).
    """

    __slots__ = (
        "id", "merceologia", "id_reparto",
        "flag1_inv", "flag2_taglio", "flag3_ing_base",
        "reparto_nome",
    )

    def __init__(self, id=None, merceologia="", id_reparto=None,
                 flag1_inv=0, flag2_taglio=0, flag3_ing_base=0, reparto_nome=None):
        self.id = id
        self.merceologia = merceologia
        self.id_reparto = id_reparto
        self.flag1_inv = int(flag1_inv) if flag1_inv is not None else 0
        self.flag2_taglio = int(flag2_taglio) if flag2_taglio is not None else 0
        self.flag3_ing_base = int(flag3_ing_base) if flag3_ing_base is not None else 0
        self.reparto_nome = reparto_nome
        
    @classmethod
    def from_row(cls, row):
        """Costruisce da una riga della tabella merceologie.

        Supporta righe con:
        - (id, merceologia, id_reparto, flag1_inv, flag2_taglio, flag3_ing_base)
        - (id, merceologia, id_reparto, flag1_inv, flag2_taglio, flag3_ing_base, reparto_nome)
        """
        if len(row) == 6:
            return cls(row[0], row[1], row[2], row[3], row[4], row[5])
        return cls(row[0], row[1], row[2], row[3], row[4], row[5], row[6])

    def params_insert(self):
        """Valori per INSERT INTO merceologie(...)."""
        return (self.merceologia, self.id_reparto, self.flag1_inv, self.flag2_taglio, self.flag3_ing_base)

    def params_update(self):
        """Valori per UPDATE merceologie ... WHERE ID = %s."""
        return (self.merceologia, self.id_reparto, self.flag1_inv, self.flag2_taglio, self.flag3_ing_base, self.id)

    @classmethod
    def fetch_all(cls, cursor):
        """Recupera tutte le merceologie."""
        cursor.execute(
            "SELECT id, merceologia, id_reparto, flag1_inv, flag2_taglio, flag3_ing_base FROM merceologie"
        )
        return [cls.from_row(row) for row in cursor.fetchall()]

    @classmethod
    def find_by_id(cls, cursor, m_id):
        """Cerca una merceologia tramite ID."""
        cursor.execute(
            "SELECT id, merceologia, id_reparto, flag1_inv, flag2_taglio, flag3_ing_base FROM merceologie WHERE id = %s",
            (m_id,),
        )
        row = cursor.fetchone()
        return cls.from_row(row) if row else None

    def insert(self, cursor, conn):
        """Inserisce il record."""
        cursor.execute(
            "INSERT INTO merceologie(merceologia, id_reparto, flag1_inv, flag2_taglio, flag3_ing_base) "
            "VALUES (%s, %s, %s, %s, %s)",
            self.params_insert(),
        )
        conn.commit()

    def save(self, cursor, conn):
        """Aggiorna il record."""
        cursor.execute(
            "UPDATE merceologie "
            "SET merceologia = %s, id_reparto = %s, flag1_inv = %s, flag2_taglio = %s, flag3_ing_base = %s "
            "WHERE id = %s",
            self.params_update(),
        )
        conn.commit()

    def delete(self, cursor, conn):
        """Elimina il record."""
        cursor.execute("DELETE FROM merceologie WHERE id = %s", (self.id,))
        conn.commit()


class Ingrediente:
    """Record ingrediente (tabella `ingredienti_base`)."""

    __slots__ = ("id", "ingrediente_base", "cod_ean", "flag1_allergene", "merceologia")

    def __init__(self, id=None, ingrediente_base="", cod_ean="", flag1_allergene=0, merceologia=""):
        self.id = id
        self.ingrediente_base = ingrediente_base
        self.cod_ean = cod_ean
        self.flag1_allergene = int(flag1_allergene)
        self.merceologia = merceologia

    @classmethod
    def from_row(cls, row):
        """Costruisce da una riga della tabella ingredienti_base."""
        return cls(row[0], row[1], row[2], row[3], row[4])

    def params_insert(self):
        """Valori per INSERT INTO ingredienti_base(...)."""
        return (self.ingrediente_base, self.cod_ean, self.flag1_allergene, self.merceologia)

    def params_update(self):
        """Valori per UPDATE ... WHERE id = %s."""
        return (self.ingrediente_base, self.cod_ean, self.flag1_allergene, self.merceologia, self.id)

    @classmethod
    def fetch_all(cls, cursor):
        """Recupera tutti gli ingredienti."""
        cursor.execute("SELECT id, ingrediente_base, cod_ean, flag1_allergene, merceologia FROM ingredienti_base")
        return [cls.from_row(row) for row in cursor.fetchall()]

    @classmethod
    def find_by_id(cls, cursor, f_id):
        """Cerca un ingrediente tramite ID."""
        cursor.execute(
            "SELECT id, ingrediente_base, cod_ean, flag1_allergene, merceologia FROM ingredienti_base WHERE id = %s",
            (f_id,),
        )
        row = cursor.fetchone()
        return cls.from_row(row) if row else None

    def save(self, cursor, conn):
        """Aggiorna il record."""
        cursor.execute(
            "UPDATE ingredienti_base SET ingrediente_base = %s, cod_ean = %s, flag1_allergene = %s, merceologia = %s WHERE id = %s",
            self.params_update(),
        )
        conn.commit()

    def delete(self, cursor, conn):
        """Elimina il record."""
        if self.id is None:
            raise ValueError("Impossibile eliminare un ingrediente privo di ID.")
        try:
            cursor.execute("DELETE FROM ingredienti_base WHERE id = %s", (self.id,))
            conn.commit()
            self.id = None
        except Exception as e:
            conn.rollback()
            raise e

    def insert(self, cursor, conn):
        """Inserisce il record."""
        try:
            cursor.execute(
                "INSERT INTO ingredienti_base (ingrediente_base, cod_ean, flag1_allergene, merceologia) VALUES (%s, %s, %s, %s)",
                self.params_insert(),
            )
            if hasattr(cursor, "lastrowid") and cursor.lastrowid:
                self.id = cursor.lastrowid
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e


class Reparto:
    """Record reparto (tabella `reparti`)."""

    __slots__ = ("id", "reparto", "flag1_dip", "flag2_prod")

    def __init__(self, id=None, reparto="", flag1_dip=0, flag2_prod=0):
        self.id = id
        self.reparto = reparto
        self.flag1_dip = int(flag1_dip)
        self.flag2_prod = int(flag2_prod)

    @classmethod
    def from_row(cls, row):
        """Costruisce da una riga della tabella reparti."""
        return cls(row[0], row[1], row[2], row[3])

    def params_insert(self):
        """Valori per INSERT INTO reparti(reparto, flag1_dip, flag2_prod)."""
        return (self.reparto, self.flag1_dip, self.flag2_prod)

    def params_update(self):
        """Valori per UPDATE ... WHERE id = %s."""
        return (self.reparto, self.flag1_dip, self.flag2_prod, self.id)

    @classmethod
    def fetch_all(cls, cursor):
        """Recupera tutti i reparti."""
        cursor.execute("SELECT id, reparto, flag1_dip, flag2_prod FROM reparti")
        return [cls.from_row(row) for row in cursor.fetchall()]

    @classmethod
    def find_by_id(cls, cursor, f_id):
        """Cerca un reparto tramite ID."""
        cursor.execute(
            "SELECT id, reparto, flag1_dip, flag2_prod FROM reparti WHERE id = %s",
            (f_id,),
        )
        row = cursor.fetchone()
        return cls.from_row(row) if row else None

    def save(self, cursor, conn):
        """Aggiorna il record."""
        cursor.execute(
            "UPDATE reparti SET reparto = %s, flag1_dip = %s, flag2_prod = %s WHERE id = %s",
            self.params_update(),
        )
        conn.commit()

    def delete(self, cursor, conn):
        """Elimina il record."""
        if self.id is None:
            raise ValueError("Impossibile eliminare un reparto privo di ID.")
        try:
            cursor.execute("DELETE FROM reparti WHERE id = %s", (self.id,))
            conn.commit()
            self.id = None
        except Exception as e:
            conn.rollback()
            raise e

    def insert(self, cursor, conn):
        """Inserisce il record."""
        try:
            cursor.execute(
                "INSERT INTO reparti (reparto, flag1_dip, flag2_prod) VALUES (%s, %s, %s)",
                self.params_insert(),
            )
            if hasattr(cursor, "lastrowid") and cursor.lastrowid:
                self.id = cursor.lastrowid
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e


class MovIngressoMerce:
    """Record movimenti per tabella `ingresso_merce`.

    Nota naming DB: nel DB la colonna del progressivo si chiama
    `progressivo_acq` (attributo Python `prog_acq`).
    """

    __slots__ = (
        "prog_acq", "data", "num_ddt", "fornitore", "taglio",
        "peso_i", "peso_f", "lotto_chiuso", "id_merc",
    )

    def __init__(self, prog_acq=None, data=None, num_ddt="", fornitore=None,
                 taglio="", peso_i=None, peso_f=None, lotto_chiuso="no", id_merc=None):
        self.prog_acq = prog_acq
        self.data = data
        self.num_ddt = num_ddt
        self.fornitore = fornitore
        self.taglio = taglio
        self.peso_i = peso_i
        self.peso_f = peso_f
        self.lotto_chiuso = lotto_chiuso
        self.id_merc = id_merc

    @classmethod
    def from_row(cls, row):
        """Costruisce un oggetto da una riga del DB."""
        if row is None:
            return None
        if len(row) == 9:
            data = row
        elif len(row) == 10:
            data = row[1:]
        else:
            raise ValueError(f"Riga non supportata per ingresso_merce: len(row)={len(row)}")
        return cls(
            prog_acq=data[0], data=data[1], num_ddt=data[2], fornitore=data[3],
            taglio=data[4], peso_i=data[5], peso_f=data[6], lotto_chiuso=data[7], id_merc=data[8],
        )

    def params_insert(self):
        """Valori per INSERT INTO ingresso_merce VALUES (%s, ...)."""
        return (self.prog_acq, self.data, self.num_ddt, self.fornitore, self.taglio,
                self.peso_i, self.peso_f, self.lotto_chiuso, self.id_merc)

    def params_where(self):
        """Valori per WHERE basata sulla chiave composta."""
        return self.params_insert()

    def params_update(self):
        """Valori per UPDATE: SET (insert) + WHERE (where)."""
        return self.params_insert() + self.params_where()

    @classmethod
    def fetch_by_progressivo(cls, cursor, progressivo_acq):
        """Recupera tutti i movimenti di un dato `progressivo_acq`."""
        cursor.execute("SELECT * FROM ingresso_merce WHERE progressivo_acq = %s", (progressivo_acq,))
        return [cls.from_row(row) for row in cursor.fetchall()]

    @classmethod
    def fetch_all(cls, cursor):
        """Recupera tutti i movimenti ordinati per data decrescente."""
        cursor.execute("SELECT * FROM ingresso_merce ORDER BY data_acq DESC, progressivo_acq DESC")
        return [cls.from_row(row) for row in cursor.fetchall()]

    @classmethod
    def find_by_key(cls, cursor, key):
        """Cerca una singola riga tramite chiave composta."""
        if isinstance(key, cls):
            params = key.params_where()
        else:
            if len(key) != 9:
                raise ValueError("Chiave composta ingresso_merce deve contenere 9 valori.")
            params = tuple(key)
        cursor.execute(
            """
            SELECT * FROM ingresso_merce
            WHERE progressivo_acq = %s
              AND data_acq = %s
              AND documento = %s
              AND fornitore = %s
              AND prodotto = %s
              AND quantita = %s
              AND residuo = %s
              AND lotto_chiuso = %s
              AND id_merc = %s
            """,
            params,
        )
        row = cursor.fetchone()
        return cls.from_row(row) if row else None

    def save(self, cursor, conn):
        """Aggiorna il record corrente tramite `progressivo_acq`."""
        update_values = self.params_insert()
        query_params = update_values + (self.prog_acq,)
        cursor.execute(
            """
            UPDATE ingresso_merce
            SET progressivo_acq = %s, data_acq = %s, documento = %s, fornitore = %s,
                prodotto = %s, quantita = %s, residuo = %s, lotto_chiuso = %s, id_merc = %s
            WHERE progressivo_acq = %s
            """,
            query_params,
        )
        conn.commit()

    def insert(self, cursor, conn):
        """Esegue INSERT del nuovo record."""
        cursor.execute(
            "INSERT INTO ingresso_merce VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            self.params_insert(),
        )
        conn.commit()

    def delete(self, cursor, conn):
        """Elimina il record tramite chiave composta."""
        cursor.execute(
            """
            DELETE FROM ingresso_merce
            WHERE progressivo_acq = %s AND data_acq = %s AND documento = %s
              AND fornitore = %s AND prodotto = %s AND quantita = %s
              AND residuo = %s AND lotto_chiuso = %s AND id_merc = %s
            """,
            self.params_where(),
        )
        conn.commit()
