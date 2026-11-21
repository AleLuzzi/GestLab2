"""Messaggi di validazione mostrati all'operatore, in italiano."""

import re


_PREFISSI_TECNICI = ("body", "query", "path", "header", "cookie")
_INGLESE = re.compile(
    r"\b(should|must|valid|field|input|expected|unable|required|missing|type|extra|none)\b",
    re.IGNORECASE,
)

_CAMPI = {
    "email": "Indirizzo email",
    "password": "Password",
    "nome": "Nome",
    "cognome": "Cognome",
    "quantita": "Quantità",
    "valore": "Quantità",
    "tipo_quantita": "Tipo di quantità",
    "prezzo": "Prezzo",
    "prezzo_unitario": "Prezzo",
    "unita_misura": "Unità di misura",
    "data_scadenza": "Scadenza",
    "data_tmc": "TMC",
    "origine": "Origine",
    "temperatura": "Temperatura",
    "lotto_id": "Lotto",
    "articolo_id": "Articolo",
    "cliente_id": "Cliente",
    "fornitore_id": "Fornitore",
    "ricetta_id": "Ricetta",
    "delta": "Delta",
    "motivo": "Motivo",
    "note": "Note",
    "ean": "Codice EAN",
    "codice": "Codice",
    "categoria": "Categoria",
    "ragione_sociale": "Ragione sociale",
    "partita_iva": "Partita IVA",
    "indirizzo": "Indirizzo",
    "laboratorio": "Laboratorio",
    "piano": "Piano",
    "ruolo": "Ruolo",
    "catalogo": "Catalogo",
    "token": "Codice di reimpostazione",
    "refresh_token": "Sessione",
    "formato": "Formato",
    "peso": "Peso",
    "data": "Data",
    "numero": "Numero",
    "tipo": "Tipo",
    "tipo_documento": "Tipo documento",
    "documento": "Documento",
    "righe": "Righe",
    "ingredienti": "Ingredienti",
    "allergeni": "Allergeni",
    "merceologia": "Merceologia",
    "reparto": "Reparto",
    "denominazione": "Denominazione",
    "telefono": "Telefono",
    "attivo": "Stato",
    "iva": "IVA",
    "aliquota_iva": "IVA",
    "giorni_vita": "Giorni di vita",
    "obbligatorio": "Obbligatorietà",
    "lotto_fornitore": "Lotto fornitore",
    "utilizzabile_come_input": "Uso come ingrediente",
}


def messaggio_validazione(errori) -> str:
    """Riduce gli errori Pydantic a frasi italiane, senza JSON né inglese."""
    frasi = []
    for errore in errori or []:
        frase = _frase(errore)
        if frase and frase not in frasi:
            frasi.append(frase)
    return " ".join(frasi) if frasi else "Dati non validi."


def _frase(errore) -> str:
    tipo = str(errore.get("type") or "")
    loc = errore.get("loc") or ()
    riga, campo = _posizione(loc)
    etichetta = _etichetta(campo)
    ctx = errore.get("ctx") or {}
    testo = _testo_personalizzato(errore.get("msg") or "")

    if tipo == "value_error" and testo and not _INGLESE.search(testo):
        return _con_riga(riga, testo)
    if "email" in tipo or (campo == "email" and tipo == "value_error"):
        return _con_riga(riga, "Indirizzo email non valido.")
    if tipo in {"json_invalid", "model_attributes_type", "model_type"} or (
        tipo == "missing" and campo is None
    ):
        return "La richiesta è incompleta o non è nel formato previsto."
    if tipo == "missing" or (tipo == "string_too_short" and _numero(ctx.get("min_length")) == 1):
        return _con_riga(riga, f"{etichetta}: campo obbligatorio.")
    if tipo == "string_too_short":
        return _con_riga(riga, f"{etichetta}: almeno {_numero(ctx.get('min_length'))} caratteri.")
    if tipo == "string_too_long":
        return _con_riga(riga, f"{etichetta}: al massimo {_numero(ctx.get('max_length'))} caratteri.")
    if tipo == "string_pattern_mismatch" or tipo in {"literal_error", "enum"}:
        return _con_riga(riga, f"{etichetta}: valore non ammesso.")
    if tipo == "greater_than":
        return _con_riga(riga, f"{etichetta}: deve essere maggiore di {_numero(ctx.get('gt'))}.")
    if tipo == "greater_than_equal":
        return _con_riga(riga, f"{etichetta}: il valore minimo è {_numero(ctx.get('ge'))}.")
    if tipo == "less_than":
        return _con_riga(riga, f"{etichetta}: deve essere minore di {_numero(ctx.get('lt'))}.")
    if tipo == "less_than_equal":
        return _con_riga(riga, f"{etichetta}: il valore massimo è {_numero(ctx.get('le'))}.")
    if tipo in {"int_parsing", "float_parsing", "decimal_parsing"}:
        return _con_riga(riga, f"{etichetta}: inserire un numero.")
    if tipo == "decimal_max_digits":
        return _con_riga(riga, f"{etichetta}: troppe cifre (massimo {_numero(ctx.get('max_digits'))}).")
    if tipo == "decimal_max_places":
        return _con_riga(riga, f"{etichetta}: al massimo {_numero(ctx.get('decimal_places'))} decimali.")
    if tipo.startswith("date") or tipo.startswith("datetime") or tipo.startswith("time"):
        return _con_riga(riga, f"{etichetta}: data non valida.")
    if tipo == "bool_parsing":
        return _con_riga(riga, f"{etichetta}: indicare sì o no.")
    if tipo == "too_short":
        return _con_riga(riga, f"Aggiungere almeno un elemento in {etichetta}.")
    if tipo == "too_long":
        return _con_riga(riga, f"{etichetta}: troppi elementi.")
    if tipo == "extra_forbidden":
        return _con_riga(riga, f"Il campo {etichetta} non è accettato.")
    if testo and not _INGLESE.search(testo):
        return _con_riga(riga, testo)
    if campo is None:
        return "Dati non validi."
    return _con_riga(riga, f"{etichetta}: valore non valido.")


def _posizione(loc):
    riga = None
    campo = None
    for parte in loc:
        if isinstance(parte, str) and parte in _PREFISSI_TECNICI:
            continue
        if isinstance(parte, int):
            riga = parte + 1
            continue
        if isinstance(parte, str):
            campo = parte
    return riga, campo


def _etichetta(campo):
    if not campo:
        return "Richiesta"
    if campo in _CAMPI:
        return _CAMPI[campo]
    return campo.replace("_", " ")


def _testo_personalizzato(msg):
    testo = str(msg).strip()
    prefisso = "Value error, "
    if testo.startswith(prefisso):
        testo = testo[len(prefisso):].strip()
    return testo


def _con_riga(riga, frase):
    if riga is None:
        return frase
    return f"Riga {riga}: {frase}"


def _numero(valore):
    if valore is None:
        return ""
    testo = str(valore)
    if testo.endswith(".0"):
        return testo[:-2]
    return testo
