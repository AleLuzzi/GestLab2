-- ============================================================================
-- Schema multi-tenant per GestLab SaaS
-- Aggiunge le tabelle di tenant/utenze/dispositivi/coda stampa e le colonne
-- tenant_id alle tabelle business esistenti (modello A: schema condiviso).
--
-- Eseguire DOPO il backup del DB locale. Ogni insert/update/select va
-- sempre filtrato per tenant_id.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Tenant (azienda/laboratorio)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenant (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(255) NOT NULL,
    piano VARCHAR(50) DEFAULT 'basic',
    attivo BOOLEAN DEFAULT TRUE,
    creato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- Utenti (admin, operatore, viewer) con tenant_id
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS utenti (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    ruolo VARCHAR(20) NOT NULL DEFAULT 'operatore',
    attivo BOOLEAN DEFAULT TRUE,
    creato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_utenti_tenant FOREIGN KEY (tenant_id) REFERENCES tenant(id)
);

-- ---------------------------------------------------------------------------
-- Dispositivi fisici che eseguono il Local Print Agent
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dispositivi_stampa (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    nome VARCHAR(255) NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    stampante_dymo VARCHAR(255),
    stampante_termica VARCHAR(255),
    ultimo_heartbeat TIMESTAMP NULL,
    CONSTRAINT fk_dispositivi_tenant FOREIGN KEY (tenant_id) REFERENCES tenant(id)
);

-- ---------------------------------------------------------------------------
-- Coda di stampa (job)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS print_jobs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    dispositivo_id BIGINT NULL,
    tipo VARCHAR(20) NOT NULL,                  -- ddt | scontrino | etichetta
    stato VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending|printing|done|error
    payload TEXT NOT NULL,                       -- JSON/ZPL/ESC-POS/PDF url
    creato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    stampato_il TIMESTAMP NULL,
    CONSTRAINT fk_printjobs_tenant FOREIGN KEY (tenant_id) REFERENCES tenant(id),
    CONSTRAINT fk_printjobs_dispositivo FOREIGN KEY (dispositivo_id)
        REFERENCES dispositivi_stampa(id)
);

-- ---------------------------------------------------------------------------
-- Aggiunta colonna tenant_id alle tabelle business (modello A)
-- Da eseguire SOLO dopo aver popolato la tabella tenant e aggiornato i dati.
-- ---------------------------------------------------------------------------
-- ALTER TABLE dipendenti     ADD COLUMN tenant_id BIGINT NULL;
-- ALTER TABLE fornitori      ADD COLUMN tenant_id BIGINT NULL;
-- ALTER TABLE tagli          ADD COLUMN tenant_id BIGINT NULL;
-- ALTER TABLE merceologie    ADD COLUMN tenant_id BIGINT NULL;
-- ALTER TABLE ingredienti_base ADD COLUMN tenant_id BIGINT NULL;
-- ALTER TABLE reparti        ADD COLUMN tenant_id BIGINT NULL;
-- ALTER TABLE ingresso_merce ADD COLUMN tenant_id BIGINT NULL;
-- ALTER TABLE prodotti       ADD COLUMN tenant_id BIGINT NULL;
-- ALTER TABLE progressivi    ADD COLUMN tenant_id BIGINT NULL;

-- Poi, per ogni tabella, valorizzare i tenant_id esistenti e aggiungere indici:
-- ALTER TABLE dipendenti ADD INDEX idx_dipendenti_tenant (tenant_id);
-- ecc.

-- ---------------------------------------------------------------------------
-- Indici di esempio (dopo l'aggiunta delle colonne)
-- ---------------------------------------------------------------------------
-- CREATE INDEX idx_ingresso_merce_tenant ON ingresso_merce(tenant_id);
-- CREATE INDEX idx_ingresso_merce_lotto  ON ingresso_merce(progressivo_acq);
