"""Pydantic schemas per le API SaaS.

Definisce i modelli di richiesta/risposta. ``tenant_id`` NON viene mai
accettato dal client: viene estratto dal JWT lato server (frontend "sottile").
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator


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
    cognome: str = ""
    email: str = ""
    reparto: int | None = None


class DipendenteUpdate(BaseModel):
    nome: str | None = None
    cognome: str | None = None
    email: str | None = None
    reparto: int | None = None


class DipendenteOut(BaseModel):
    id: int | None = None
    nome: str
    cognome: str = ""
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
#  Articoli e ingressi tracciati
# ------------------------------------------------------------------------- #

class ArticoloCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=120)
    codice: str | None = Field(default=None, max_length=60)
    categoria: str | None = Field(default=None, max_length=80)
    unita_misura: str = Field(default="kg", min_length=1, max_length=8)
    utilizzabile_come_input: bool = True


class ArticoloUpdate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=120)
    codice: str | None = Field(default=None, max_length=60)
    categoria: str | None = Field(default=None, max_length=80)
    unita_misura: str = Field(..., min_length=1, max_length=8)
    attivo: bool = True
    utilizzabile_come_input: bool | None = None


class ArticoloOut(BaseModel):
    id: int
    codice: str | None = None
    nome: str
    categoria: str | None = None
    unita_misura: str
    attivo: bool
    utilizzabile_come_input: bool


class IngressoTracciatoRigaCreate(BaseModel):
    articolo_id: int = Field(..., gt=0)
    quantita: Decimal = Field(..., gt=0, max_digits=12, decimal_places=3)


class IngressoTracciatoCreate(BaseModel):
    data: date
    numero_ddt: str = Field(default="", max_length=40)
    fornitore_id: int = Field(..., gt=0)
    righe: list[IngressoTracciatoRigaCreate] = Field(..., min_length=1)


class LavorazioneInputCreate(BaseModel):
    lotto_id: int = Field(..., gt=0)
    quantita: Decimal = Field(..., gt=0, max_digits=12, decimal_places=3)


class LavorazioneOutputCreate(BaseModel):
    articolo_id: int = Field(..., gt=0)
    quantita: Decimal = Field(..., gt=0, max_digits=12, decimal_places=3)


class LavorazioneScartoCreate(BaseModel):
    descrizione: str = Field(..., min_length=1, max_length=120)
    quantita: Decimal = Field(..., gt=0, max_digits=12, decimal_places=3)
    unita_misura: str = Field(..., min_length=1, max_length=8)


class LavorazioneCreate(BaseModel):
    data: date
    descrizione: str = Field(default="", max_length=255)
    operatore_id: int = Field(..., gt=0)
    input: list[LavorazioneInputCreate] = Field(..., min_length=1)
    output: list[LavorazioneOutputCreate] = Field(..., min_length=1)
    scarti: list[LavorazioneScartoCreate] = Field(default_factory=list)


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
    soggetto_id: int | None = None
    azienda: str
    flag1_ing_merce: int = 0
    flag2_inventario: int = 0


class SoggettoCreate(BaseModel):
    denominazione: str = Field(..., min_length=1, max_length=255)
    tipo_soggetto: str = Field(default="azienda", max_length=20)
    nome: str | None = Field(default=None, max_length=100)
    cognome: str | None = Field(default=None, max_length=100)
    partita_iva: str | None = Field(default=None, max_length=20)
    codice_fiscale: str | None = Field(default=None, max_length=20)
    indirizzo: str | None = Field(default=None, max_length=255)
    numero_civico: str | None = Field(default=None, max_length=20)
    cap: str | None = Field(default=None, max_length=20)
    citta: str | None = Field(default=None, max_length=100)
    provincia: str | None = Field(default=None, max_length=100)
    paese: str | None = Field(default="Italia", max_length=100)
    email: str | None = Field(default=None, max_length=255)
    telefono: str | None = Field(default=None, max_length=30)
    codice_destinatario: str | None = Field(default=None, max_length=7)
    pec: str | None = Field(default=None, max_length=255)
    ruolo_cliente: bool = False
    ruolo_fornitore: bool = False
    flag1_ing_merce: bool = False
    flag2_inventario: bool = False
    attivo: bool = True

    @field_validator("denominazione")
    @classmethod
    def denominazione_non_vuota(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("La denominazione è obbligatoria.")
        return value

    @field_validator("tipo_soggetto")
    @classmethod
    def tipo_soggetto_valido(cls, value):
        if value not in {"azienda", "persona"}:
            raise ValueError("Il tipo soggetto deve essere 'azienda' o 'persona'.")
        return value


class SoggettoUpdate(BaseModel):
    denominazione: str | None = Field(default=None, min_length=1, max_length=255)
    tipo_soggetto: str | None = Field(default=None, max_length=20)
    nome: str | None = Field(default=None, max_length=100)
    cognome: str | None = Field(default=None, max_length=100)
    partita_iva: str | None = Field(default=None, max_length=20)
    codice_fiscale: str | None = Field(default=None, max_length=20)
    indirizzo: str | None = Field(default=None, max_length=255)
    numero_civico: str | None = Field(default=None, max_length=20)
    cap: str | None = Field(default=None, max_length=20)
    citta: str | None = Field(default=None, max_length=100)
    provincia: str | None = Field(default=None, max_length=100)
    paese: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    telefono: str | None = Field(default=None, max_length=30)
    codice_destinatario: str | None = Field(default=None, max_length=7)
    pec: str | None = Field(default=None, max_length=255)
    ruolo_cliente: bool | None = None
    ruolo_fornitore: bool | None = None
    flag1_ing_merce: bool | None = None
    flag2_inventario: bool | None = None
    attivo: bool | None = None

    @field_validator("denominazione")
    @classmethod
    def denominazione_non_vuota(cls, value):
        if value is None:
            raise ValueError("La denominazione è obbligatoria.")
        value = value.strip()
        if not value:
            raise ValueError("La denominazione è obbligatoria.")
        return value

    @field_validator("tipo_soggetto")
    @classmethod
    def tipo_soggetto_valido(cls, value):
        if value is None or value not in {"azienda", "persona"}:
            raise ValueError("Il tipo soggetto deve essere 'azienda' o 'persona'.")
        return value

    @field_validator(
        "ruolo_cliente",
        "ruolo_fornitore",
        "flag1_ing_merce",
        "flag2_inventario",
        "attivo",
    )
    @classmethod
    def booleani_non_nulli(cls, value):
        if value is None:
            raise ValueError("I campi booleani non possono essere nulli.")
        return value


class SoggettoOut(SoggettoCreate):
    id: int
    tenant_id: int
    fornitore_legacy_id: int | None = None


# ------------------------------------------------------------------------- #
#  Progressivi
# ------------------------------------------------------------------------- #

class ProgressiviWrite(BaseModel):
    prog_acq: int = Field(..., ge=0, le=2147483647)
    prog_ven: int = Field(..., ge=0, le=2147483647)


class ProgressiviOut(BaseModel):
    prog_acq: int | None = None
    prog_ven: int | None = None


# ------------------------------------------------------------------------- #
#  Ingresso merce
# ------------------------------------------------------------------------- #

class IngressoMerceRigaCreate(BaseModel):
    taglio: str = Field(..., min_length=1, max_length=30)
    peso: Decimal = Field(..., gt=0, max_digits=6, decimal_places=2)
    id_merc: int = Field(..., gt=0)

    @field_validator("peso")
    @classmethod
    def peso_entra_nella_colonna(cls, value):
        if len(format(value, "f")) > 6:
            raise ValueError("Il peso supera i 6 caratteri consentiti.")
        return value


class IngressoMerceCreate(BaseModel):
    prog_acq: str = Field(..., min_length=1, max_length=5)
    data: date
    num_ddt: str = Field(default="", max_length=8)
    fornitore_id: int = Field(..., gt=0)
    righe: list[IngressoMerceRigaCreate] = Field(..., min_length=1)


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
