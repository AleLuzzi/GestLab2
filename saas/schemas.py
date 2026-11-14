"""Pydantic schemas per le API SaaS.

Definisce i modelli di richiesta/risposta. ``tenant_id`` NON viene mai
accettato dal client: viene estratto dal JWT lato server (frontend "sottile").
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


ALLERGENI_RICETTA = (
    "glutine",
    "crostacei",
    "uova",
    "pesce",
    "arachidi",
    "soia",
    "latte",
    "frutta_a_guscio",
    "sedano",
    "senape",
    "sesamo",
    "solfiti",
    "lupini",
    "molluschi",
)


# ------------------------------------------------------------------------- #
#  Auth
# ------------------------------------------------------------------------- #

class ModelloAPI(BaseModel):
    """Base dei modelli API.

    Un ``tenant_id`` nel body è rifiutato, salvo i modelli di risposta che
    lo espongono perché lo ha calcolato il server. L'autorità resta il JWT.
    """

    @model_validator(mode="before")
    @classmethod
    def rifiuta_tenant_indicato_dal_client(cls, data):
        if (
            isinstance(data, dict)
            and "tenant_id" in data
            and "tenant_id" not in cls.model_fields
        ):
            raise ValueError(
                "Il tenant non si indica nella richiesta: arriva dal token di accesso."
            )
        return data


class LoginRequest(ModelloAPI):
    email: EmailStr
    password: str


class AuditLogOut(ModelloAPI):
    id: int
    utente_email: str
    azione: str
    entita: str
    entita_id: str | None = None
    dettaglio: str | None = None
    creato_il: datetime | None = None


class TokenResponse(ModelloAPI):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    # Info utente restituite direttamente dal server: il frontend NON deve
    # decodificare il JWT per ottenere ruolo/tenant (piu' robusto e sicuro).
    email: str
    ruolo: str
    tenant_id: int


class RefreshRequest(ModelloAPI):
    refresh_token: str


class LogoutRequest(ModelloAPI):
    refresh_token: str


# ------------------------------------------------------------------------- #
#  Tenant / Utenti (solo admin)
# ------------------------------------------------------------------------- #

class TenantCreate(ModelloAPI):
    nome: str = Field(..., min_length=1, max_length=255)
    piano: str = "basic"


class OnboardingRichiesta(ModelloAPI):
    """Dati per l'onboarding interno di un laboratorio."""

    nome: str = Field(..., min_length=1, max_length=255)
    piano: str = Field(default="basic", pattern="^(basic|pro|enterprise)$")
    ragione_sociale: str = Field(..., min_length=1, max_length=255)
    indirizzo: str = Field(..., min_length=1, max_length=255)
    laboratorio: str = Field(..., min_length=1, max_length=255)
    partita_iva: str = Field(..., min_length=11, max_length=11)
    email: EmailStr
    password: str
    catalogo: str = Field(default="vuoto", pattern="^(vuoto|macelleria)$")

    @field_validator("nome", "ragione_sociale", "indirizzo", "laboratorio", "partita_iva")
    @classmethod
    def normalizza_testo(cls, value):
        return value.strip()

    @field_validator("partita_iva")
    @classmethod
    def valida_partita_iva(cls, value):
        if not value.isdigit() or len(value) != 11:
            raise ValueError("La partita IVA deve essere di 11 cifre.")
        return value


class TenantOsaUpdate(ModelloAPI):
    ragione_sociale: str = Field(default="", max_length=255)
    indirizzo: str = Field(default="", max_length=255)
    laboratorio: str = Field(default="", max_length=255)
    partita_iva: str = Field(default="", max_length=20)

    @field_validator("ragione_sociale", "indirizzo", "laboratorio", "partita_iva")
    @classmethod
    def normalizza_dato_osa(cls, value):
        return value.strip()


class UtenteCreate(ModelloAPI):
    email: EmailStr
    password: str
    ruolo: str = Field(default="operatore", pattern="^(admin|operatore|viewer)$")


class PasswordDimenticataRequest(ModelloAPI):
    email: EmailStr


class PasswordReimpostaRequest(ModelloAPI):
    token: str = Field(..., min_length=20, max_length=200)
    password: str


class MessaggioResponse(ModelloAPI):
    messaggio: str


# ------------------------------------------------------------------------- #
#  Dipendenti
# ------------------------------------------------------------------------- #

class DipendenteCreate(ModelloAPI):
    nome: str = Field(..., min_length=1)
    cognome: str = ""
    email: str = ""
    reparto: int | None = None


class DipendenteUpdate(ModelloAPI):
    nome: str | None = None
    cognome: str | None = None
    email: str | None = None
    reparto: int | None = None


class DipendenteOut(ModelloAPI):
    id: int | None = None
    nome: str
    cognome: str = ""
    email: str
    reparto: int | None = None
    reparto_nome: str | None = None


# ------------------------------------------------------------------------- #
#  Merceologie
# ------------------------------------------------------------------------- #

class MerceologiaCreate(ModelloAPI):
    merceologia: str = Field(..., min_length=1, max_length=255)
    reparto: int | None = None


class MerceologiaUpdate(ModelloAPI):
    merceologia: str | None = None
    reparto: int | None = None


class MerceologiaOut(ModelloAPI):
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

class ArticoloCreate(ModelloAPI):
    nome: str = Field(..., min_length=1, max_length=120)
    codice: str | None = Field(default=None, max_length=60)
    categoria: str | None = Field(default=None, max_length=80)
    unita_misura: str = Field(default="kg", min_length=1, max_length=8)
    ean: str | None = Field(default=None, max_length=32)
    prezzo_unitario: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    utilizzabile_come_input: bool = True


class ArticoloUpdate(ModelloAPI):
    nome: str = Field(..., min_length=1, max_length=120)
    codice: str | None = Field(default=None, max_length=60)
    categoria: str | None = Field(default=None, max_length=80)
    unita_misura: str = Field(..., min_length=1, max_length=8)
    ean: str | None = Field(default=None, max_length=32)
    prezzo_unitario: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    attivo: bool = True
    utilizzabile_come_input: bool | None = None


class ArticoloOut(ModelloAPI):
    id: int
    codice: str | None = None
    nome: str
    categoria: str | None = None
    unita_misura: str
    ean: str | None = None
    prezzo_unitario: Decimal | None = None
    attivo: bool
    utilizzabile_come_input: bool


class ListinoArticoloOut(ModelloAPI):
    id: int
    codice: str | None = None
    nome: str
    categoria: str | None = None
    unita_misura: str
    prezzo_unitario: Decimal | None = None
    quantita_disponibile: Decimal
    lotti_disponibili: int
    disponibile: bool


class RicettaIngredienteCreate(ModelloAPI):
    articolo_id: int = Field(..., gt=0)
    tipo_quantita: str = Field(..., pattern="^(quantita|percentuale)$")
    valore: Decimal = Field(..., gt=0, max_digits=12, decimal_places=3)
    obbligatorio: bool = True

    @model_validator(mode="after")
    def valida_percentuale(self):
        if self.tipo_quantita == "percentuale" and self.valore > 100:
            raise ValueError("La percentuale dell'ingrediente non puo' superare 100")
        return self


class RicettaIngredienteOut(ModelloAPI):
    articolo_id: int
    articolo_nome: str
    unita_misura: str
    tipo_quantita: str
    valore: Decimal
    obbligatorio: bool


class RicettaCreate(ModelloAPI):
    nome: str = Field(..., min_length=1, max_length=120)
    articolo_id: int = Field(..., gt=0)
    resa_attesa: Decimal = Field(..., gt=0, max_digits=12, decimal_places=3)
    scarto_atteso: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=3)
    ingredienti: list[RicettaIngredienteCreate] = Field(default_factory=list)
    allergeni: list[str] = Field(default_factory=list)
    giorni_vita: int | None = Field(default=None, gt=0)
    istruzioni_conservazione: str | None = Field(default=None, max_length=1000)
    istruzioni_cottura: str | None = Field(default=None, max_length=1000)

    @field_validator("nome")
    @classmethod
    def normalizza_nome(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Il nome della ricetta non puo' essere vuoto")
        return value

    @field_validator("ingredienti")
    @classmethod
    def valida_ingredienti_univoci(cls, value):
        articolo_ids = [ingrediente.articolo_id for ingrediente in value]
        if len(articolo_ids) != len(set(articolo_ids)):
            raise ValueError("Ogni articolo puo' comparire una sola volta nella ricetta")
        return value

    @field_validator("allergeni")
    @classmethod
    def valida_allergeni(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("Ogni allergene puo' comparire una sola volta")
        allergeni_non_validi = set(value) - set(ALLERGENI_RICETTA)
        if allergeni_non_validi:
            raise ValueError("La ricetta contiene un allergene non riconosciuto")
        return value

    @field_validator("istruzioni_conservazione", "istruzioni_cottura")
    @classmethod
    def normalizza_istruzioni(cls, value):
        if value is None:
            return None
        value = value.strip()
        return value or None


class RicettaUpdate(RicettaCreate):
    attiva: bool = True


class RicettaOut(ModelloAPI):
    id: int
    nome: str
    articolo_id: int
    articolo_nome: str
    unita_misura: str
    resa_attesa: Decimal
    scarto_atteso: Decimal
    attiva: bool
    ingredienti: list[RicettaIngredienteOut] = Field(default_factory=list)
    allergeni: list[str] = Field(default_factory=list)
    giorni_vita: int | None = None
    istruzioni_conservazione: str | None = None
    istruzioni_cottura: str | None = None


class IngressoTracciatoRigaCreate(ModelloAPI):
    articolo_id: int = Field(..., gt=0)
    quantita: Decimal = Field(..., gt=0, max_digits=12, decimal_places=3)
    lotto_fornitore: str | None = Field(default=None, max_length=64)
    origine: str | None = Field(default=None, max_length=255)
    data_scadenza: date | None = None
    data_tmc: date | None = None
    temperatura_ingresso: Decimal | None = Field(default=None, ge=-100, le=100, max_digits=6, decimal_places=2)
    note_lotto: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def valida_tipo_data(self):
        if self.data_scadenza is not None and self.data_tmc is not None:
            raise ValueError("Indicare la scadenza oppure il TMC, non entrambi")
        return self


class IngressoTracciatoCreate(ModelloAPI):
    data: date
    numero_ddt: str = Field(default="", max_length=40)
    fornitore_id: int = Field(..., gt=0)
    righe: list[IngressoTracciatoRigaCreate] = Field(..., min_length=1)


class LavorazioneInputCreate(ModelloAPI):
    lotto_id: int = Field(..., gt=0)
    quantita: Decimal = Field(..., gt=0, max_digits=12, decimal_places=3)
    conferma_tmc_scaduto: bool = False


class LavorazioneOutputCreate(ModelloAPI):
    articolo_id: int = Field(..., gt=0)
    quantita: Decimal = Field(..., gt=0, max_digits=12, decimal_places=3)
    origine: str | None = Field(default=None, max_length=255)
    data_scadenza: date | None = None
    data_tmc: date | None = None

    @model_validator(mode="after")
    def valida_tipo_data(self):
        if self.data_scadenza is not None and self.data_tmc is not None:
            raise ValueError("Indicare la scadenza oppure il TMC, non entrambi")
        return self


class LavorazioneScartoCreate(ModelloAPI):
    descrizione: str = Field(..., min_length=1, max_length=120)
    quantita: Decimal = Field(..., gt=0, max_digits=12, decimal_places=3)
    unita_misura: str = Field(..., min_length=1, max_length=8)


class LavorazioneCreate(ModelloAPI):
    data: date
    descrizione: str = Field(default="", max_length=255)
    operatore_id: int = Field(..., gt=0)
    ricetta_id: int | None = Field(default=None, gt=0)
    input: list[LavorazioneInputCreate] = Field(..., min_length=1)
    output: list[LavorazioneOutputCreate] = Field(..., min_length=1)
    scarti: list[LavorazioneScartoCreate] = Field(default_factory=list)


class RettificaLottoCreate(ModelloAPI):
    delta: Decimal = Field(..., max_digits=12, decimal_places=3)
    motivo: str = Field(..., pattern="^(inventario|calo|reso|errore)$")

    @field_validator("delta")
    @classmethod
    def valida_delta_non_zero(cls, value):
        if value == 0:
            raise ValueError("Il delta della rettifica non può essere zero")
        return value


class VenditaCreate(ModelloAPI):
    data: date
    cliente_id: int | None = Field(default=None, gt=0)
    tipo_documento: str = Field(..., pattern="^(DDT|RICEVUTA)$")

    @model_validator(mode="after")
    def valida_destinatario_ddt(self):
        if self.tipo_documento == "DDT" and self.cliente_id is None:
            raise ValueError("Per un DDT è necessario selezionare un cliente.")
        return self


class VenditaRigaCreate(ModelloAPI):
    lotto_id: int = Field(..., gt=0)
    articolo_id: int = Field(..., gt=0)
    quantita: Decimal = Field(..., gt=0, max_digits=12, decimal_places=3)
    unita_misura: str = Field(..., min_length=1, max_length=8)
    prezzo_unitario: Decimal = Field(..., ge=0, max_digits=12, decimal_places=4)
    iva_percentuale: Decimal = Field(
        default=Decimal("0.00"), ge=0, le=100, max_digits=5, decimal_places=2
    )


class VenditaRigheCreate(ModelloAPI):
    righe: list[VenditaRigaCreate] = Field(..., min_length=1)


class VenditaCompletaCreate(VenditaCreate):
    righe: list[VenditaRigaCreate] = Field(..., min_length=1)


# ------------------------------------------------------------------------- #
#  Reparti
# ------------------------------------------------------------------------- #

class RepartoCreate(ModelloAPI):
    reparto: str = Field(..., min_length=1, max_length=255)
    flag1_dip: int = 0
    flag2_prod: int = 0


class RepartoUpdate(ModelloAPI):
    reparto: str | None = None
    flag1_dip: int | None = None
    flag2_prod: int | None = None


class RepartoOut(ModelloAPI):
    id: int | None = None
    reparto: str
    flag1_dip: int = 0
    flag2_prod: int = 0


# ------------------------------------------------------------------------- #
#  Fornitori
# ------------------------------------------------------------------------- #

class FornitoreCreate(ModelloAPI):
    azienda: str = Field(..., min_length=1, max_length=50)
    flag1_ing_merce: int = 0
    flag2_inventario: int = 0


class FornitoreUpdate(ModelloAPI):
    azienda: str | None = None
    flag1_ing_merce: int | None = None
    flag2_inventario: int | None = None


class FornitoreOut(ModelloAPI):
    id: int | None = None
    soggetto_id: int | None = None
    azienda: str
    flag1_ing_merce: int = 0
    flag2_inventario: int = 0


class SoggettoCreate(ModelloAPI):
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


class SoggettoUpdate(ModelloAPI):
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

class ProgressiviWrite(ModelloAPI):
    prog_acq: int = Field(..., ge=0, le=2147483647)
    prog_ven: int = Field(..., ge=0, le=2147483647)


class ProgressiviOut(ModelloAPI):
    prog_acq: int | None = None
    prog_ven: int | None = None


# ------------------------------------------------------------------------- #
#  Ingresso merce
# ------------------------------------------------------------------------- #

class IngressoMerceRigaCreate(ModelloAPI):
    taglio: str = Field(..., min_length=1, max_length=30)
    peso: Decimal = Field(..., gt=0, max_digits=6, decimal_places=2)
    id_merc: int = Field(..., gt=0)

    @field_validator("peso")
    @classmethod
    def peso_entra_nella_colonna(cls, value):
        if len(format(value, "f")) > 6:
            raise ValueError("Il peso supera i 6 caratteri consentiti.")
        return value


class IngressoMerceCreate(ModelloAPI):
    prog_acq: str = Field(..., min_length=1, max_length=5)
    data: date
    num_ddt: str = Field(default="", max_length=8)
    fornitore_id: int = Field(..., gt=0)
    righe: list[IngressoMerceRigaCreate] = Field(..., min_length=1)


# ------------------------------------------------------------------------- #
#  Stampa (DDT, scontrini, etichette) e barcode
# ------------------------------------------------------------------------- #

class DdtRiga(ModelloAPI):
    prodotto: str = ""
    taglio: str = ""
    quantita: str = ""
    peso: str = ""


class DdtCreate(ModelloAPI):
    numero: str
    data: str | None = None
    fornitore: str = ""
    righe: list[DdtRiga] = []


class ScontrinoRiga(ModelloAPI):
    descrizione: str = ""
    prezzo: str = ""
    qta: str = ""


class ScontrinoCreate(ModelloAPI):
    testata: str = ""
    righe: list[ScontrinoRiga] = []
    totale: str = "0.00"
    iva: str = "0.00"


class EtichettaCreate(ModelloAPI):
    plu: str = ""
    prodotto: str = ""
    prezzo_kg: str = ""
    ingredienti: str | None = Field(default=None, max_length=1000)
    codice: str = ""
    lotto_id: int | None = None
    lotto: str = ""
    scadenza: str = ""
    origine: str = ""
    allergeni: list[str] | None = None
    conservazione: str = Field(default="", max_length=1000)
    peso: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=3)

    @field_validator("allergeni")
    @classmethod
    def valida_allergeni_etichetta(cls, value):
        if value is None:
            return value
        if len(value) != len(set(value)):
            raise ValueError("Ogni allergene puo' comparire una sola volta")
        if set(value) - set(ALLERGENI_RICETTA):
            raise ValueError("L'etichetta contiene un allergene non riconosciuto")
        return value


# ------------------------------------------------------------------------- #
#  Coda di stampa (print_jobs) e dispositivi
# ------------------------------------------------------------------------- #

class DispositivoCreate(ModelloAPI):
    nome: str = Field(..., min_length=1, max_length=255)
    stampante_dymo: str = ""
    stampante_termica: str = ""


class PrintJobCreate(ModelloAPI):
    tipo: str = Field(..., pattern="^(ddt|scontrino|etichetta)$")
    payload: str = Field(..., min_length=1)


class PrintJobOut(ModelloAPI):
    id: int
    tenant_id: int
    dispositivo_id: int | None = None
    tipo: str
    stato: str
    payload: str
    creato_il: str | None = None
    stampato_il: str | None = None
