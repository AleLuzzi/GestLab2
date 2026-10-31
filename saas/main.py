"""Main FastAPI per il backend SaaS di GestLab.

Riutilizza il core applicativo (``core.services``) esponendo le API REST
multi-tenant. Avvio: ``python -m uvicorn saas.main:app --reload``

L'autenticazione estrae il ``tenant_id`` dal JWT; i repository del core
filtrano tutti i dati per ``tenant_id`` (multi-tenancy reale, modello A:
schema condiviso). Il client non deve mai inviare il ``tenant_id``.
"""

import logging
import os
import uuid
from datetime import date
from logging.handlers import RotatingFileHandler

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from saas import auth
from saas.repositories import print_repo, tenant_repo, tracciabilita_repo
from saas.schemas import (
    DdtCreate,
    DipendenteCreate,
    DipendenteOut,
    DipendenteUpdate,
    DispositivoCreate,
    EtichettaCreate,
    LoginRequest,
    MerceologiaCreate,
    MerceologiaOut,
    MerceologiaUpdate,
    PrintJobCreate,
    PrintJobOut,
    ProgressiviOut,
    ProgressiviWrite,
    RepartoCreate,
    RepartoOut,
    RepartoUpdate,
    FornitoreCreate,
    FornitoreOut,
    FornitoreUpdate,
    IngressoMerceCreate,
    ArticoloCreate,
    ArticoloOut,
    ArticoloUpdate,
    IngressoTracciatoCreate,
    LavorazioneCreate,
    RefreshRequest,
    ScontrinoCreate,
    SoggettoCreate,
    SoggettoOut,
    SoggettoUpdate,
    TenantCreate,
    TokenResponse,
    UtenteCreate,
)

from core.repositories.soggetti import FornitoreConStoricoError
from core.services import dipendenti as dipendenti_service
from core.services import merceologie as merceologie_service
from core.services import reparti as reparti_service
from core.services import fornitori as fornitori_service
from core.services import lotti as lotti_service
from core.services import menu as menu_service
from core.services import printing as printing_service
from core.services import barcode as barcode_service
from core.services import progressivi as progressivi_service
from core.services import ingresso_merce as ingresso_merce_service
from core.services import soggetti as soggetti_service
from core.repositories.ingresso_merce_repo import FornitoreNonValido
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG_DIR = os.environ.get("GESTLAB_LOG_DIR", os.path.join(_PROJECT_DIR, "logs"))
os.makedirs(_LOG_DIR, exist_ok=True)

logger = logging.getLogger("gestlab.saas")
logger.setLevel(logging.INFO)
logger.propagate = False
if not any(getattr(handler, "_gestlab_file_handler", False) for handler in logger.handlers):
    file_handler = RotatingFileHandler(
        os.path.join(_LOG_DIR, "gestlab-saas.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler._gestlab_file_handler = True
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    logger.addHandler(file_handler)

app = FastAPI(
    title="GestLab SaaS API",
    description="API REST multi-tenant per la gestione laboratorio.",
    version="0.1.0",
)

# ------------------------------------------------------------------------- #
#  Web App frontend (static files)
# ------------------------------------------------------------------------- #
# Serve la console web (SPA vanilla) dalla cartella `web/`. Gli asset sono
# raggiungibili sotto /static e la radice restituisce index.html.
_WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
app.mount("/static", StaticFiles(directory=_WEB_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(os.path.join(_WEB_DIR, "index.html"))


# ------------------------------------------------------------------------- #
#  Auth
# ------------------------------------------------------------------------- #

@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    """Autentica un utente e restituisce access + refresh token."""
    utente = tenant_repo.trova_utente_by_email(payload.email)
    if not utente or not utente["attivo"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenziali non valide")

    if not auth.verify_password(payload.password, utente["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenziali non valide")

    access = auth.create_token(
        utente["email"], utente["tenant_id"], utente["ruolo"], "access"
    )
    refresh = auth.create_token(
        utente["email"], utente["tenant_id"], utente["ruolo"], "refresh"
    )
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        email=utente["email"],
        ruolo=utente["ruolo"],
        tenant_id=utente["tenant_id"],
    )


@app.post("/auth/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshRequest):
    """Rigenera access (e refresh) token da un refresh token valido."""
    info = auth.decode_token(payload.refresh_token)
    if info.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token non di refresh")

    access = auth.create_token(
        info["sub"], info["tenant_id"], info["ruolo"], "access"
    )
    refresh = auth.create_token(
        info["sub"], info["tenant_id"], info["ruolo"], "refresh"
    )
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        email=info["sub"],
        ruolo=info["ruolo"],
        tenant_id=info["tenant_id"],
    )


# ------------------------------------------------------------------------- #
#  Tenant / Utenti (solo admin)
# ------------------------------------------------------------------------- #

@app.post("/api/v1/tenant", status_code=status.HTTP_201_CREATED)
def crea_tenant(
    payload: TenantCreate,
    user: dict = Depends(auth.require_roles("admin")),
):
    """Crea un nuovo tenant (solo admin)."""
    tenant_id = tenant_repo.crea_tenant(payload.nome, payload.piano)
    return {"id": tenant_id, "nome": payload.nome, "piano": payload.piano}


@app.post("/api/v1/utenti", status_code=status.HTTP_201_CREATED)
def crea_utente(
    payload: UtenteCreate,
    user: dict = Depends(auth.require_roles("admin")),
):
    """Crea un utente nel tenant dell'admin corrente."""
    tenant_id = user["tenant_id"]
    password_hash = auth.hash_password(payload.password)
    utente_id = tenant_repo.crea_utente(
        tenant_id, payload.email, password_hash, payload.ruolo
    )
    return {"id": utente_id, "email": payload.email, "ruolo": payload.ruolo}


# ------------------------------------------------------------------------- #
#  Dipendenti
# ------------------------------------------------------------------------- #

@app.get("/api/v1/dipendenti", response_model=list[DipendenteOut])
def lista_dipendenti(user: dict = Depends(auth.get_current_user)):
    """Elenco dipendenti del tenant corrente."""
    dipendenti = dipendenti_service.lista_dipendenti(user["tenant_id"])
    return [
        DipendenteOut(id=d.id, nome=d.nome, cognome=d.cognome, email=d.email, reparto=d.reparto,
                      reparto_nome=d.reparto_nome)
        for d in dipendenti
    ]


@app.post("/api/v1/dipendenti", response_model=DipendenteOut, status_code=status.HTTP_201_CREATED)
def crea_dipendente(
    payload: DipendenteCreate,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Crea un nuovo dipendente nel tenant corrente."""
    nuovo = dipendenti_service.crea_dipendente(
        nome=payload.nome,
        email=payload.email,
        reparto=payload.reparto,
        tenant_id=user["tenant_id"],
        cognome=payload.cognome,
    )
    return DipendenteOut(
        id=nuovo.id,
        nome=nuovo.nome,
        cognome=nuovo.cognome,
        email=nuovo.email,
        reparto=nuovo.reparto,
    )


@app.put("/api/v1/dipendenti/{dipendente_id}", response_model=DipendenteOut)
def aggiorna_dipendente(
    dipendente_id: int,
    payload: DipendenteUpdate,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Aggiorna un dipendente esistente del tenant corrente."""
    dipendente = dipendenti_service.trova_dipendente(dipendente_id, user["tenant_id"])
    if not dipendente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dipendente non trovato")

    dipendenti_service.aggiorna_dipendente(
        dipendente,
        nome=payload.nome,
        cognome=payload.cognome,
        email=payload.email,
        reparto=payload.reparto,
        tenant_id=user["tenant_id"],
    )
    return DipendenteOut(id=dipendente.id, nome=dipendente.nome,
                         cognome=dipendente.cognome,
                         email=dipendente.email, reparto=dipendente.reparto)


@app.delete("/api/v1/dipendenti/{dipendente_id}", status_code=status.HTTP_204_NO_CONTENT)
def elimina_dipendente(
    dipendente_id: int,
    user: dict = Depends(auth.require_roles("admin")),
):
    """Elimina un dipendente (solo admin). Audit log da aggiungere."""
    dipendente = dipendenti_service.trova_dipendente(dipendente_id, user["tenant_id"])
    if not dipendente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dipendente non trovato")
    dipendenti_service.elimina_dipendente(dipendente, user["tenant_id"])


# ------------------------------------------------------------------------- #
#  Merceologie
# ------------------------------------------------------------------------- #

@app.get("/api/v1/merceologie", response_model=list[MerceologiaOut])
def lista_merceologie(user: dict = Depends(auth.get_current_user)):
    """Elenco merceologie del tenant corrente."""
    merceologie = merceologie_service.lista_merceologie(user["tenant_id"])
    return [
        MerceologiaOut(
            id=m.id,
            merceologia=m.merceologia,
            reparto=m.id_reparto,
            flag1_inv=m.flag1_inv,       
            flag2_taglio=m.flag2_taglio, 
            flag3_ing_base=m.flag3_ing_base,
            reparto_nome=m.reparto_nome,
        )
        for m in merceologie
    ]


@app.post("/api/v1/merceologie", response_model=MerceologiaOut, status_code=status.HTTP_201_CREATED)
def crea_merceologia(
    payload: MerceologiaCreate,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Crea una nuova merceologia nel tenant corrente."""
    nuovo = merceologie_service.crea_merceologia(
        merceologia=payload.merceologia,
        id_reparto=payload.reparto,
        tenant_id=user["tenant_id"],
    )
    return MerceologiaOut(
        id=nuovo.id,
        merceologia=nuovo.merceologia,
        reparto=nuovo.id_reparto,
        reparto_nome=nuovo.reparto_nome,
    )


@app.put("/api/v1/merceologie/{merceologia_id}", response_model=MerceologiaOut)
def aggiorna_merceologia(
    merceologia_id: int,
    payload: MerceologiaUpdate,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Aggiorna una merceologia esistente del tenant corrente."""
    merceologia = merceologie_service.trova_merceologia(merceologia_id, user["tenant_id"])
    if not merceologia:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Merceologia non trovata")

    merceologie_service.aggiorna_merceologia(
        merceologia,
        merceologia_nome=payload.merceologia,
        id_reparto=payload.reparto,
        tenant_id=user["tenant_id"],
    )
    return MerceologiaOut(
        id=merceologia.id,
        merceologia=merceologia.merceologia,
        reparto=merceologia.id_reparto,
        reparto_nome=merceologia.reparto_nome,
    )


@app.delete("/api/v1/merceologie/{merceologia_id}", status_code=status.HTTP_204_NO_CONTENT)
def elimina_merceologia(
    merceologia_id: int,
    user: dict = Depends(auth.require_roles("admin")),
):
    """Elimina una merceologia del tenant corrente."""
    merceologia = merceologie_service.trova_merceologia(merceologia_id, user["tenant_id"])
    if not merceologia:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Merceologia non trovata")
    merceologie_service.elimina_merceologia(merceologia, user["tenant_id"])


# ------------------------------------------------------------------------- #
#  Articoli
# ------------------------------------------------------------------------- #

@app.get("/api/v1/articoli", response_model=list[ArticoloOut])
def lista_articoli(user: dict = Depends(auth.get_current_user)):
    """Elenco articoli del tenant corrente."""
    return tracciabilita_repo.lista_articoli(user["tenant_id"])


@app.post(
    "/api/v1/articoli",
    response_model=ArticoloOut,
    status_code=status.HTTP_201_CREATED,
)
def crea_articolo(
    payload: ArticoloCreate,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Crea un articolo nel tenant corrente."""
    return tracciabilita_repo.crea_articolo(
        user["tenant_id"],
        payload.codice,
        payload.nome,
        payload.categoria,
        payload.unita_misura,
        payload.utilizzabile_come_input,
    )


@app.put("/api/v1/articoli/{articolo_id}", response_model=ArticoloOut)
def aggiorna_articolo(
    articolo_id: int,
    payload: ArticoloUpdate,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Aggiorna un articolo del tenant corrente."""
    articolo = tracciabilita_repo.aggiorna_articolo(
        user["tenant_id"],
        articolo_id,
        payload.codice,
        payload.nome,
        payload.categoria,
        payload.unita_misura,
        payload.attivo,
        payload.utilizzabile_come_input,
    )
    if articolo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Articolo non trovato")
    return articolo


@app.delete("/api/v1/articoli/{articolo_id}", status_code=status.HTTP_204_NO_CONTENT)
def disattiva_articolo(
    articolo_id: int,
    user: dict = Depends(auth.require_roles("admin")),
):
    """Disattiva un articolo preservando i riferimenti dei lotti storici."""
    if not tracciabilita_repo.disattiva_articolo(user["tenant_id"], articolo_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Articolo non trovato")


# ------------------------------------------------------------------------- #
#  Reparti
# ------------------------------------------------------------------------- #

@app.get("/api/v1/reparti", response_model=list[RepartoOut])
def lista_reparti(user: dict = Depends(auth.get_current_user)):
    """Elenco reparti del tenant corrente."""
    reparti = reparti_service.lista_reparti(user["tenant_id"])
    return [
        RepartoOut(id=r.id, reparto=r.reparto, flag1_dip=r.flag1_dip, flag2_prod=r.flag2_prod)
        for r in reparti
    ]


@app.post("/api/v1/reparti", response_model=RepartoOut, status_code=status.HTTP_201_CREATED)
def crea_reparto(
    payload: RepartoCreate,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Crea un nuovo reparto nel tenant corrente."""
    nuovo = reparti_service.crea_reparto(
        payload.reparto,
        payload.flag1_dip,
        payload.flag2_prod,
        user["tenant_id"],
    )
    return RepartoOut(id=nuovo.id, reparto=nuovo.reparto, flag1_dip=nuovo.flag1_dip, flag2_prod=nuovo.flag2_prod)


@app.put("/api/v1/reparti/{reparto_id}", response_model=RepartoOut)
def aggiorna_reparto(
    reparto_id: int,
    payload: RepartoUpdate,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Aggiorna un reparto esistente del tenant corrente."""
    reparto = reparti_service.trova_reparto(reparto_id, user["tenant_id"])
    if not reparto:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reparto non trovato")

    reparti_service.aggiorna_reparto(
        reparto,
        nome=payload.reparto,
        flag1_dip=payload.flag1_dip,
        flag2_prod=payload.flag2_prod,
        tenant_id=user["tenant_id"],
    )
    return RepartoOut(id=reparto.id, reparto=reparto.reparto, flag1_dip=reparto.flag1_dip, flag2_prod=reparto.flag2_prod)


@app.delete("/api/v1/reparti/{reparto_id}", status_code=status.HTTP_204_NO_CONTENT)
def elimina_reparto(
    reparto_id: int,
    user: dict = Depends(auth.require_roles("admin")),
):
    """Elimina un reparto del tenant corrente."""
    reparto = reparti_service.trova_reparto(reparto_id, user["tenant_id"])
    if not reparto:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reparto non trovato")
    reparti_service.elimina_reparto(reparto, user["tenant_id"])


# ------------------------------------------------------------------------- #
#  Fornitori
# ------------------------------------------------------------------------- #

@app.get("/api/v1/soggetti", response_model=list[SoggettoOut])
def lista_soggetti(user: dict = Depends(auth.get_current_user)):
    """Elenco anagrafiche del tenant corrente."""
    return soggetti_service.lista_soggetti(user["tenant_id"])


@app.post(
    "/api/v1/soggetti",
    response_model=SoggettoOut,
    status_code=status.HTTP_201_CREATED,
)
def crea_soggetto(
    payload: SoggettoCreate,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Crea un'anagrafica con uno o entrambi i ruoli."""
    try:
        return soggetti_service.crea_soggetto(user["tenant_id"], payload.model_dump())
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error


@app.put("/api/v1/soggetti/{soggetto_id}", response_model=SoggettoOut)
def aggiorna_soggetto(
    soggetto_id: int,
    payload: SoggettoUpdate,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Aggiorna i dati anagrafici e i ruoli di un soggetto."""
    esistente = soggetti_service.trova_soggetto(user["tenant_id"], soggetto_id)
    if not esistente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Anagrafica non trovata")

    dati = {
        campo: esistente[campo]
        for campo in (
            "denominazione",
            "tipo_soggetto",
            "nome",
            "cognome",
            "partita_iva",
            "codice_fiscale",
            "indirizzo",
            "numero_civico",
            "cap",
            "citta",
            "provincia",
            "paese",
            "email",
            "telefono",
            "codice_destinatario",
            "pec",
            "ruolo_cliente",
            "ruolo_fornitore",
            "flag1_ing_merce",
            "flag2_inventario",
            "attivo",
        )
    }
    dati.update(payload.model_dump(exclude_unset=True))
    try:
        aggiornato = soggetti_service.aggiorna_soggetto(
            user["tenant_id"], soggetto_id, dati
        )
    except FornitoreConStoricoError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error
    if not aggiornato:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Anagrafica non trovata")
    return aggiornato


@app.delete(
    "/api/v1/soggetti/{soggetto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def disattiva_soggetto(
    soggetto_id: int,
    user: dict = Depends(auth.require_roles("admin")),
):
    """Disattiva l'anagrafica senza cancellare lo storico documentale."""
    if not soggetti_service.disattiva_soggetto(user["tenant_id"], soggetto_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Anagrafica non trovata")


@app.get("/api/v1/fornitori", response_model=list[FornitoreOut])
def lista_fornitori(user: dict = Depends(auth.get_current_user)):
    """Elenco fornitori del tenant corrente."""
    fornitori = fornitori_service.lista_fornitori(user["tenant_id"])
    return [
        FornitoreOut(
            id=f.id,
            soggetto_id=f.soggetto_id,
            azienda=f.azienda,
            flag1_ing_merce=f.flag1_ing_merce,
            flag2_inventario=f.flag2_inventario,
        )
        for f in fornitori
    ]


@app.post("/api/v1/fornitori", response_model=FornitoreOut, status_code=status.HTTP_201_CREATED)
def crea_fornitore(
    payload: FornitoreCreate,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Crea un nuovo fornitore nel tenant corrente."""
    nuovo = fornitori_service.crea_fornitore(
        payload.azienda,
        payload.flag1_ing_merce,
        payload.flag2_inventario,
        user["tenant_id"],
    )
    return FornitoreOut(
        id=nuovo.id,
        soggetto_id=nuovo.soggetto_id,
        azienda=nuovo.azienda,
        flag1_ing_merce=nuovo.flag1_ing_merce,
        flag2_inventario=nuovo.flag2_inventario,
    )


@app.put("/api/v1/fornitori/{fornitore_id}", response_model=FornitoreOut)
def aggiorna_fornitore(
    fornitore_id: int,
    payload: FornitoreUpdate,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Aggiorna un fornitore esistente del tenant corrente."""
    fornitore = fornitori_service.trova_fornitore(fornitore_id, user["tenant_id"])
    if not fornitore:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fornitore non trovato")

    fornitori_service.aggiorna_fornitore(
        fornitore,
        azienda=payload.azienda,
        flag1_ing_merce=payload.flag1_ing_merce,
        flag2_inventario=payload.flag2_inventario,
        tenant_id=user["tenant_id"],
    )
    return FornitoreOut(
        id=fornitore.id,
        soggetto_id=fornitore.soggetto_id,
        azienda=fornitore.azienda,
        flag1_ing_merce=fornitore.flag1_ing_merce,
        flag2_inventario=fornitore.flag2_inventario,
    )


@app.delete("/api/v1/fornitori/{fornitore_id}", status_code=status.HTTP_204_NO_CONTENT)
def elimina_fornitore(
    fornitore_id: int,
    user: dict = Depends(auth.require_roles("admin")),
):
    """Elimina un fornitore del tenant corrente."""
    fornitore = fornitori_service.trova_fornitore(fornitore_id, user["tenant_id"])
    if not fornitore:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fornitore non trovato")
    fornitori_service.elimina_fornitore(fornitore, user["tenant_id"])


# ------------------------------------------------------------------------- #
#  Progressivi
# ------------------------------------------------------------------------- #

def _progressivi_tenant(tenant_id: int):
    """Restituisce il singolo record del tenant, segnalando dati ambigui."""
    records = progressivi_service.lista_progressivi(tenant_id)
    if len(records) > 1:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Sono presenti più record progressivi per questo tenant",
        )
    return records


@app.get("/api/v1/progressivi", response_model=list[ProgressiviOut])
def lista_progressivi(user: dict = Depends(auth.get_current_user)):
    """Legge i contatori del tenant corrente."""
    return [
        ProgressiviOut(prog_acq=record.prog_acq, prog_ven=record.prog_ven)
        for record in _progressivi_tenant(user["tenant_id"])
    ]


@app.post(
    "/api/v1/progressivi",
    response_model=ProgressiviOut,
    status_code=status.HTTP_201_CREATED,
)
def crea_progressivi(
    payload: ProgressiviWrite,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Inizializza i contatori del tenant corrente."""
    if _progressivi_tenant(user["tenant_id"]):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "I progressivi per questo tenant esistono già",
        )
    nuovo = progressivi_service.crea_progressivi(
        payload.prog_acq, payload.prog_ven, user["tenant_id"]
    )
    return ProgressiviOut(prog_acq=nuovo.prog_acq, prog_ven=nuovo.prog_ven)


@app.put("/api/v1/progressivi", response_model=ProgressiviOut)
def aggiorna_progressivi(
    payload: ProgressiviWrite,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Aggiorna i contatori del tenant corrente."""
    records = _progressivi_tenant(user["tenant_id"])
    if not records:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Progressivi non trovati")
    aggiornato = progressivi_service.aggiorna_progressivi(
        records[0],
        prog_acq=payload.prog_acq,
        prog_ven=payload.prog_ven,
        tenant_id=user["tenant_id"],
    )
    return ProgressiviOut(prog_acq=aggiornato.prog_acq, prog_ven=aggiornato.prog_ven)


@app.delete("/api/v1/progressivi", status_code=status.HTTP_204_NO_CONTENT)
def elimina_progressivi(user: dict = Depends(auth.require_roles("admin"))):
    """Elimina i contatori del tenant corrente."""
    records = _progressivi_tenant(user["tenant_id"])
    if not records:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Progressivi non trovati")
    progressivi_service.elimina_progressivi(records[0], user["tenant_id"])


# ------------------------------------------------------------------------- #
#  Ingresso merce
# ------------------------------------------------------------------------- #

@app.post("/api/v1/ingresso-merce", status_code=status.HTTP_201_CREATED)
def conferma_ingresso_merce(
    payload: IngressoMerceCreate,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Salva tutte le righe dell'ingresso nel tenant autenticato."""
    try:
        movimenti = ingresso_merce_service.salva_movimenti(
            prog_acq=payload.prog_acq,
            data=payload.data,
            num_ddt=payload.num_ddt,
            fornitore_id=payload.fornitore_id,
            righe=payload.righe,
            tenant_id=user["tenant_id"],
        )
    except FornitoreNonValido as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Fornitore non trovato, disattivato o non abilitato all'ingresso merce",
        ) from error
    return {"inseriti": len(movimenti)}


@app.post(
    "/api/v1/tracciabilita/ingressi",
    status_code=status.HTTP_201_CREATED,
)
def registra_ingresso_tracciato(
    payload: IngressoTracciatoCreate,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Registra il documento d'ingresso e crea i relativi lotti tracciati."""
    try:
        return tracciabilita_repo.registra_ingresso(
            tenant_id=user["tenant_id"],
            data=payload.data,
            numero_ddt=payload.numero_ddt,
            fornitore_id=payload.fornitore_id,
            righe=payload.righe,
        )
    except FornitoreNonValido as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Fornitore non trovato, disattivato o non abilitato all'ingresso merce",
        ) from error
    except tracciabilita_repo.ArticoloNonTrovato as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Uno o più articoli non esistono o non sono attivi",
        ) from error
    except Exception as error:
        riferimento = uuid.uuid4().hex
        logger.exception(
            "Errore durante il salvataggio dell'ingresso tracciato "
            "reference=%s tenant_id=%s numero_righe=%s",
            riferimento,
            user["tenant_id"],
            len(payload.righe),
        )
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Errore interno durante il salvataggio dell'ingresso. "
            f"Riferimento assistenza: {riferimento}",
        ) from error


@app.get("/api/v1/tracciabilita/lotti")
def lista_lotti_tracciati(
    solo_disponibili: bool = False,
    data_dal: date | None = None,
    data_al: date | None = None,
    user: dict = Depends(auth.get_current_user),
):
    """Elenca i lotti del tenant, filtrabili per data e giacenza disponibile."""
    if data_dal is not None and data_al is not None and data_dal > data_al:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "La data iniziale non può essere successiva alla data finale.",
        )
    return tracciabilita_repo.lista_lotti(
        user["tenant_id"],
        solo_disponibili=solo_disponibili,
        data_dal=data_dal,
        data_al=data_al,
    )


@app.get("/api/v1/tracciabilita/lotti/{lotto_id}")
def dettaglio_lotto_tracciato(
    lotto_id: int,
    user: dict = Depends(auth.get_current_user),
):
    """Restituisce origine, lavorazione e movimenti del lotto."""
    dettaglio = tracciabilita_repo.dettaglio_lotto(user["tenant_id"], lotto_id)
    if dettaglio is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lotto non trovato")
    return dettaglio


@app.post(
    "/api/v1/tracciabilita/lavorazioni",
    status_code=status.HTTP_201_CREATED,
)
def registra_lavorazione_tracciata(
    payload: LavorazioneCreate,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Registra la trasformazione dei lotti e i prodotti ottenuti."""
    try:
        return tracciabilita_repo.registra_lavorazione(
            tenant_id=user["tenant_id"],
            data=payload.data,
            descrizione=payload.descrizione,
            operatore_id=payload.operatore_id,
            input_lavorazione=payload.input,
            output=payload.output,
            scarti=payload.scarti,
        )
    except tracciabilita_repo.DipendenteNonTrovato as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "L'operatore non esiste nel tenant corrente",
        ) from error
    except tracciabilita_repo.ArticoloNonTrovato as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Uno o più articoli non esistono o non sono attivi",
        ) from error
    except tracciabilita_repo.LottoNonTrovato as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Uno o più lotti non esistono",
        ) from error
    except tracciabilita_repo.GiacenzaInsufficiente as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    except tracciabilita_repo.ArticoloNonUtilizzabileComeInput as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


# ------------------------------------------------------------------------- #
#  Lotti / Menu (sola lettura per ora)
# ------------------------------------------------------------------------- #

@app.get("/api/v1/lotti/aperti")
def lotti_aperti(user: dict = Depends(auth.get_current_user)):
    """Lotti aperti del tenant corrente."""
    return lotti_service.lotti_aperti(user["tenant_id"])


@app.get("/api/v1/menu")
def menu(user: dict = Depends(auth.get_current_user)):
    """Prodotti del menu del tenant corrente, raggruppati per merceologia."""
    return menu_service.prodotti_menu(user["tenant_id"])


# ------------------------------------------------------------------------- #
#  Stampa (DDT, scontrini, etichette) e barcode
# ------------------------------------------------------------------------- #

@app.post("/api/v1/ddt", response_class=Response)
def genera_ddt(
    payload: DdtCreate,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Genera il PDF di un DDT per il tenant corrente.

    Restituisce il PDF (application/pdf). In produzione il file va salvato su
    Object Storage e il job inoltrato alla coda ``print_jobs`` per il Local
    Print Agent.
    """
    righe = [r.model_dump() for r in payload.righe]
    pdf = printing_service.genera_ddt_pdf(
        numero=payload.numero,
        data=payload.data,
        fornitore=payload.fornitore,
        righe=righe,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="ddt_{payload.numero}.pdf"'},
    )


@app.post("/api/v1/scontrino", response_class=Response)
def genera_scontrino(
    payload: ScontrinoCreate,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Genera lo scontrino termico (ESC/POS) per il tenant corrente."""
    righe = [r.model_dump() for r in payload.righe]
    escpos = printing_service.genera_scontrino_escpos(
        testata=payload.testata,
        righe=righe,
        totale=payload.totale,
        iva=payload.iva,
    )
    return Response(
        content=escpos,
        media_type="application/octet-stream",
        headers={"Content-Disposition": 'attachment; filename="scontrino.bin"'},
    )


@app.post("/api/v1/etichetta", response_class=Response)
def genera_etichetta(
    payload: EtichettaCreate,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Genera il PDF di un'etichetta DYMO per il tenant corrente."""
    pdf = printing_service.genera_etichetta_dymo_pdf(
        plu=payload.plu,
        prodotto=payload.prodotto,
        prezzo_kg=payload.prezzo_kg,
        ingredienti=payload.ingredienti,
        codice=payload.codice,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="etichetta_{payload.plu}.pdf"'},
    )


@app.get("/api/v1/prodotti/ean/{codice}")
def cerca_prodotto_ean(
    codice: str,
    user: dict = Depends(auth.get_current_user),
):
    """Lookup di un prodotto tramite codice EAN (scoped al tenant)."""
    prodotto = barcode_service.lookup_prodotto(codice, user["tenant_id"])
    if not prodotto:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prodotto non trovato")
    return prodotto


# ------------------------------------------------------------------------- #
#  Coda di stampa (print_jobs) e dispositivi
# ------------------------------------------------------------------------- #

@app.post("/api/v1/dispositivi", status_code=status.HTTP_201_CREATED)
def registra_dispositivo(
    payload: DispositivoCreate,
    user: dict = Depends(auth.require_roles("admin")),
):
    """Registra un Local Print Agent per il tenant corrente (solo admin).

    Genera un token univoco per il dispositivo: l'agent lo usera' per
    autenticarsi e prelevare i job dalla coda.
    """
    import secrets
    token = secrets.token_urlsafe(32)
    dispositivo_id = print_repo.registra_dispositivo(
        user["tenant_id"],
        payload.nome,
        token,
        payload.stampante_dymo,
        payload.stampante_termica,
    )
    return {
        "id": dispositivo_id,
        "nome": payload.nome,
        "token": token,
        "stampante_dymo": payload.stampante_dymo,
        "stampante_termica": payload.stampante_termica,
    }


@app.post("/api/v1/print-jobs", response_model=PrintJobOut, status_code=status.HTTP_201_CREATED)
def accoda_stampa(
    payload: PrintJobCreate,
    user: dict = Depends(auth.require_roles("admin", "operatore")),
):
    """Accoda un job di stampa per il tenant corrente.

    Il payload e' il contenuto del documento (JSON/PDF url/ESC-POS) che il
    Local Print Agent andra' a stampare sull'hardware locale.
    """
    job_id = print_repo.accoda_job(
        user["tenant_id"], None, payload.tipo, payload.payload
    )
    return PrintJobOut(
        id=job_id,
        tenant_id=user["tenant_id"],
        tipo=payload.tipo,
        stato="pending",
        payload=payload.payload,
    )


@app.get("/api/v1/print-jobs", response_model=list[PrintJobOut])
def elenca_stampe(
    stato: str | None = None,
    user: dict = Depends(auth.get_current_user),
):
    """Elenco dei job di stampa del tenant corrente (opzionale filtro stato)."""
    jobs = print_repo.elenca_job(user["tenant_id"], stato=stato)
    return [PrintJobOut(**j) for j in jobs]


@app.get("/api/v1/print-jobs/{job_id}", status_code=status.HTTP_200_OK)
def stato_job(
    job_id: int,
    user: dict = Depends(auth.get_current_user),
):
    """Stato di un singolo job di stampa del tenant corrente."""
    jobs = print_repo.elenca_job(user["tenant_id"])
    job = next((j for j in jobs if j["id"] == job_id), None)
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job non trovato")
    return job


# ------------------------------------------------------------------------- #
#  Endpoint per il Local Print Agent (autenticazione via token dispositivo)
# ------------------------------------------------------------------------- #

@app.get("/agent/next-job")
def agent_next_job(token: str):
    """L'agent preleva il prossimo job 'pending' (autenticato via token).

    Il token identifica il dispositivo di stampa registrato. Se il dispositivo
    non esiste, risponde 401.
    """
    dispositivo = print_repo.trova_dispositivo_by_token(token)
    if not dispositivo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token dispositivo non valido")

    print_repo.aggiorna_heartbeat(dispositivo["id"])
    job = print_repo.prendi_prossimo_job(dispositivo["id"])
    if not job:
        return {"job": None}
    return {"job": job}


@app.post("/agent/{job_id}/done")
def agent_job_done(
    job_id: int,
    token: str,
):
    """L'agent segnala che un job e' stato stampato (stato 'done')."""
    dispositivo = print_repo.trova_dispositivo_by_token(token)
    if not dispositivo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token dispositivo non valido")

    print_repo.aggiorna_stato_job(job_id, "done")
    return {"ok": True}


@app.post("/agent/{job_id}/error")
def agent_job_error(
    job_id: int,
    token: str,
    detail: str = "",
):
    """L'agent segnala un errore di stampa per un job."""
    dispositivo = print_repo.trova_dispositivo_by_token(token)
    if not dispositivo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token dispositivo non valido")

    print_repo.aggiorna_stato_job(job_id, "error")
    return {"ok": True, "detail": detail}


@app.get("/health")
def health():
    """Health check per il load balancer / orchestrazione."""
    return {"status": "ok"}
