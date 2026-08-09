"""Main FastAPI per il backend SaaS di GestLab.

Riutilizza il core applicativo (``core.services``) esponendo le API REST
multi-tenant. Avvio: ``python -m uvicorn saas.main:app --reload``

L'autenticazione estrae il ``tenant_id`` dal JWT; i repository del core
filtrano tutti i dati per ``tenant_id`` (multi-tenancy reale, modello A:
schema condiviso). Il client non deve mai inviare il ``tenant_id``.
"""

import os

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from saas import auth, tenant_repo, print_repo
from saas.schemas import (
    DdtCreate,
    DipendenteCreate,
    DipendenteOut,
    DipendenteUpdate,
    DispositivoCreate,
    EtichettaCreate,
    LoginRequest,
    PrintJobCreate,
    PrintJobOut,
    RefreshRequest,
    ScontrinoCreate,
    TenantCreate,
    TokenResponse,
    UtenteCreate,
)

from core.services import dipendenti as dipendenti_service
from core.services import lotti as lotti_service
from core.services import menu as menu_service
from core.services import printing as printing_service
from core.services import barcode as barcode_service

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
        DipendenteOut(id=d.id, nome=d.nome, email=d.email, reparto=d.reparto,
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
        payload.nome, payload.email, payload.reparto, user["tenant_id"]
    )
    return DipendenteOut(id=nuovo.id, nome=nuovo.nome, email=nuovo.email, reparto=nuovo.reparto)


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
        email=payload.email,
        reparto=payload.reparto,
        tenant_id=user["tenant_id"],
    )
    return DipendenteOut(id=dipendente.id, nome=dipendente.nome,
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
