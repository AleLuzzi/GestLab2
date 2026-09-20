"""Pydantic schemas per le API SaaS.

Definisce i modelli di richiesta/risposta. ``tenant_id`` NON viene mai
accettato dal client: viene estratto dal JWT lato server (frontend "sottile").
"""

from pydantic import BaseModel, EmailStr, Field


# ------------------------------------------------------------------------- #
#  Auth
# ------------------------------------------------------------------------- #

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    # Info utente restituite direttamente dal server: il frontend NON deve
    # decodificare il JWT per ottenere ruolo/tenant (piu' robusto e sicuro).
    email: str
    ruolo: str
    tenant_id: int


class RefreshRequest(BaseModel):
    refresh_token: str


# ------------------------------------------------------------------------- #
#  Tenant / Utenti (solo admin)
# ------------------------------------------------------------------------- #

class TenantCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=255)
    piano: str = "basic"


class UtenteCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    ruolo: str = Field(default="operatore", pattern="^(admin|operatore|viewer)$")


# ------------------------------------------------------------------------- #
#  Dipendenti
# ------------------------------------------------------------------------- #

class DipendenteCreate(BaseModel):
    nome: str = Field(..., min_length=1)
    email: str = ""
    reparto: int | None = None


class DipendenteUpdate(BaseModel):
    nome: str | None = None
    email: str | None = None
    reparto: int | None = None


class DipendenteOut(BaseModel):
    id: int | None = None
    nome: str
    email: str
    reparto: int | None = None
    reparto_nome: str | None = None


# ------------------------------------------------------------------------- #
#  Merceologie
# ------------------------------------------------------------------------- #

class MerceologiaCreate(BaseModel):
    merceologia: str = Field(..., min_length=1, max_length=255)
    reparto: int | None = None


class MerceologiaUpdate(BaseModel):
    merceologia: str | None = None
    reparto: int | None = None


class MerceologiaOut(BaseModel):
    id: int | None = None
    merceologia: str
    reparto: int | None = None
    flag1_inv: int = 0        
    flag2_taglio: int = 0     
    flag3_ing_base: int = 0  
    reparto_nome: str | None = None 


# ------------------------------------------------------------------------- #
#  Tagli
# ------------------------------------------------------------------------- #

class TaglioCreate(BaseModel):
    taglio: str = Field(..., min_length=1, max_length=255)
    id_merceologia: int | None = None


class TaglioUpdate(BaseModel):
    taglio: str | None = None
    id_merceologia: int | None = None


class TaglioOut(BaseModel):
    id: int | None = None
    taglio: str
    id_merceologia: int | None = None
    merceologia_nome: str | None = None


# ------------------------------------------------------------------------- #
#  Reparti
# ------------------------------------------------------------------------- #

class RepartoCreate(BaseModel):
    reparto: str = Field(..., min_length=1, max_length=255)
    flag1_dip: int = 0
    flag2_prod: int = 0


class RepartoUpdate(BaseModel):
    reparto: str | None = None
    flag1_dip: int | None = None
    flag2_prod: int | None = None


class RepartoOut(BaseModel):
    id: int | None = None
    reparto: str
    flag1_dip: int = 0
    flag2_prod: int = 0


# ------------------------------------------------------------------------- #
#  Fornitori
# ------------------------------------------------------------------------- #

class FornitoreCreate(BaseModel):
    azienda: str = Field(..., min_length=1, max_length=50)
    flag1_ing_merce: int = 0
    flag2_inventario: int = 0


class FornitoreUpdate(BaseModel):
    azienda: str | None = None
    flag1_ing_merce: int | None = None
    flag2_inventario: int | None = None


class FornitoreOut(BaseModel):
    id: int | None = None
    azienda: str
    flag1_ing_merce: int = 0
    flag2_inventario: int = 0


# ------------------------------------------------------------------------- #
#  Stampa (DDT, scontrini, etichette) e barcode
# ------------------------------------------------------------------------- #

class DdtRiga(BaseModel):
    prodotto: str = ""
    taglio: str = ""
    quantita: str = ""
    peso: str = ""


class DdtCreate(BaseModel):
    numero: str
    data: str | None = None
    fornitore: str = ""
    righe: list[DdtRiga] = []


class ScontrinoRiga(BaseModel):
    descrizione: str = ""
    prezzo: str = ""
    qta: str = ""


class ScontrinoCreate(BaseModel):
    testata: str = ""
    righe: list[ScontrinoRiga] = []
    totale: str = "0.00"
    iva: str = "0.00"


class EtichettaCreate(BaseModel):
    plu: str
    prodotto: str
    prezzo_kg: str = ""
    ingredienti: str = ""
    codice: str = ""


# ------------------------------------------------------------------------- #
#  Coda di stampa (print_jobs) e dispositivi
# ------------------------------------------------------------------------- #

class DispositivoCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=255)
    stampante_dymo: str = ""
    stampante_termica: str = ""


class PrintJobCreate(BaseModel):
    tipo: str = Field(..., pattern="^(ddt|scontrino|etichetta)$")
    payload: str = Field(..., min_length=1)


class PrintJobOut(BaseModel):
    id: int
    tenant_id: int
    dispositivo_id: int | None = None
    tipo: str
    stato: str
    payload: str
    creato_il: str | None = None
    stampato_il: str | None = None
