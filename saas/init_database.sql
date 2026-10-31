-- ============================================================================
-- GestLab2 Unified Database Schema (dev + SaaS)
-- 
-- Single-file initialization for both local development and cloud deployment.
-- Combines business tables and multi-tenant infrastructure in dependency order.
--
-- Idempotent: use `CREATE TABLE IF NOT EXISTS` to safely run multiple times.
-- Generated: 2026-09-11
-- ============================================================================

SET FOREIGN_KEY_CHECKS=0;

-- ---------------------------------------------------------------------------
-- 1. TENANT & AUTH LAYER (parents for all other tables)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `tenant` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `nome` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `piano` varchar(50) COLLATE utf8mb4_general_ci DEFAULT 'basic',
  `attivo` tinyint(1) DEFAULT 1,
  `creato_il` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `utenti` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `email` varchar(255) COLLATE utf8mb4_general_ci NOT NULL UNIQUE,
  `password_hash` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `ruolo` varchar(20) COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'operatore',
  `attivo` tinyint(1) DEFAULT 1,
  `creato_il` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_utenti_tenant` (`tenant_id`),
  CONSTRAINT `fk_utenti_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `tenant` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ---------------------------------------------------------------------------
-- 2. PRINT INFRASTRUCTURE (depends on tenant)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `dispositivi_stampa` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `nome` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `token` varchar(255) COLLATE utf8mb4_general_ci NOT NULL UNIQUE,
  `stampante_dymo` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `stampante_termica` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `ultimo_heartbeat` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_dispositivi_tenant` (`tenant_id`),
  CONSTRAINT `fk_dispositivi_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `tenant` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `print_jobs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `dispositivo_id` bigint NULL,
  `tipo` varchar(20) COLLATE utf8mb4_general_ci NOT NULL,
  `stato` varchar(20) COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'pending',
  `payload` text COLLATE utf8mb4_general_ci NOT NULL,
  `creato_il` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `stampato_il` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_printjobs_tenant` (`tenant_id`),
  KEY `fk_printjobs_dispositivo` (`dispositivo_id`),
  CONSTRAINT `fk_printjobs_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `tenant` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_printjobs_dispositivo` FOREIGN KEY (`dispositivo_id`) REFERENCES `dispositivi_stampa` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ---------------------------------------------------------------------------
-- 3. BUSINESS TABLES (multi-tenant, with tenant_id filtering)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `soggetti` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `denominazione` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `tipo_soggetto` varchar(20) COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'azienda',
  `nome` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `cognome` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `partita_iva` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `codice_fiscale` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `indirizzo` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `numero_civico` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `cap` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `citta` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `provincia` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `paese` varchar(100) COLLATE utf8mb4_general_ci DEFAULT 'Italia',
  `email` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `telefono` varchar(30) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `codice_destinatario` varchar(7) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `pec` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `attivo` tinyint(1) NOT NULL DEFAULT 1,
  `creato_il` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `aggiornato_il` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_soggetti_tenant_id` (`tenant_id`, `id`),
  KEY `idx_soggetti_partita_iva` (`tenant_id`, `partita_iva`),
  CONSTRAINT `fk_soggetti_tenant` FOREIGN KEY (`tenant_id`)
    REFERENCES `tenant` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `soggetti_ruoli` (
  `tenant_id` bigint NOT NULL,
  `soggetto_id` bigint NOT NULL,
  `ruolo` varchar(20) COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`tenant_id`, `soggetto_id`, `ruolo`),
  CONSTRAINT `fk_soggetti_ruoli_soggetto` FOREIGN KEY (`tenant_id`, `soggetto_id`)
    REFERENCES `soggetti` (`tenant_id`, `id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `reparti` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `reparto` varchar(15) DEFAULT NULL,
  `flag1_dip` int DEFAULT NULL,
  `flag2_prod` int DEFAULT NULL,
  `tenant_id` bigint DEFAULT NULL,
  PRIMARY KEY (`ID`),
  KEY `idx_tenant_id` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

CREATE TABLE IF NOT EXISTS `dipendenti` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(25) DEFAULT NULL,
  `cognome` varchar(25) DEFAULT NULL,
  `reparto` int DEFAULT NULL,
  `email` varchar(50) DEFAULT NULL,
  `tenant_id` bigint DEFAULT NULL,
  PRIMARY KEY (`ID`),
  KEY `idx_tenant_id` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

CREATE TABLE IF NOT EXISTS `fornitori` (
  `ID` int NOT NULL AUTO_INCREMENT,
  -- Compatibility mirror; the canonical value is soggetti.denominazione.
  `azienda` varchar(50) DEFAULT NULL,
  `flag1_ing_merce` int DEFAULT NULL,
  `flag2_inventario` int NOT NULL,
  `tenant_id` bigint DEFAULT NULL,
  `soggetto_id` bigint DEFAULT NULL,
  PRIMARY KEY (`ID`),
  KEY `idx_tenant_id` (`tenant_id`),
  UNIQUE KEY `uq_fornitori_tenant_id` (`tenant_id`, `ID`),
  UNIQUE KEY `uq_fornitori_soggetto` (`tenant_id`, `soggetto_id`),
  CONSTRAINT `fk_fornitori_soggetto` FOREIGN KEY (`tenant_id`, `soggetto_id`)
    REFERENCES `soggetti` (`tenant_id`, `id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

CREATE TABLE IF NOT EXISTS `merceologie` (
  `Id` int NOT NULL AUTO_INCREMENT,
  `merceologia` varchar(23) DEFAULT NULL,
  `Id_Reparto` int DEFAULT NULL,
  `flag1_inv` int DEFAULT NULL,
  `flag2_taglio` int DEFAULT NULL,
  `flag3_ing_base` int DEFAULT NULL,
  `tenant_id` bigint DEFAULT NULL,
  PRIMARY KEY (`Id`),
  KEY `Id` (`Id`),
  KEY `Id_2` (`Id`),
  KEY `idx_merceologie_tenant` (`tenant_id`),
  KEY `idx_tenant_id` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

CREATE TABLE IF NOT EXISTS `articoli` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `codice` varchar(60) DEFAULT NULL,
  `nome` varchar(120) NOT NULL,
  `categoria` varchar(80) DEFAULT NULL,
  `unita_misura` varchar(8) NOT NULL DEFAULT 'kg',
  `attivo` tinyint(1) NOT NULL DEFAULT 1,
  `utilizzabile_come_input` tinyint(1) NOT NULL DEFAULT 1,
  `creato_il` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_articoli_tenant_id` (`tenant_id`, `id`),
  UNIQUE KEY `uq_articoli_tenant_codice` (`tenant_id`, `codice`),
  KEY `idx_articoli_tenant_nome` (`tenant_id`, `nome`),
  CONSTRAINT `fk_articoli_tenant` FOREIGN KEY (`tenant_id`)
    REFERENCES `tenant` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `prodotti` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `prodotto` varchar(30) DEFAULT NULL,
  `reparto` varchar(11) DEFAULT NULL,
  `plu` varchar(5) DEFAULT NULL,
  `prezzo1` int DEFAULT NULL,
  `prezzo2` varchar(1) DEFAULT NULL,
  `prezzo3` varchar(1) DEFAULT NULL,
  `prezzo4` varchar(1) DEFAULT NULL,
  `prezzo_straord` varchar(1) DEFAULT NULL,
  `gruppo_merc` varchar(1) DEFAULT NULL,
  `tara` varchar(1) DEFAULT NULL,
  `gg_cons_1` varchar(3) DEFAULT NULL,
  `gg_cons_2` varchar(1) DEFAULT NULL,
  `ean` varchar(7) DEFAULT NULL,
  `testo_agg_1` int DEFAULT NULL,
  `testo_agg_2` int DEFAULT NULL,
  `testo_agg_3` int DEFAULT NULL,
  `testo_agg_4` int DEFAULT NULL,
  `pz_x_scatola` int DEFAULT NULL,
  `peso_fisso` int DEFAULT NULL,
  `num_offerta` int DEFAULT NULL,
  `art_in_pubblic` int DEFAULT NULL,
  `sovrascritt_prezzo` int DEFAULT NULL,
  `stile_tracc` int DEFAULT NULL,
  `rich_stm_traccia` int DEFAULT NULL,
  `riga_1` varchar(55) DEFAULT NULL,
  `riga_2` varchar(41) DEFAULT NULL,
  `riga_3` varchar(32) DEFAULT NULL,
  `riga_4` varchar(5) DEFAULT NULL,
  `formato_1` int DEFAULT NULL,
  `formato_2` int DEFAULT NULL,
  `formato_3` int DEFAULT NULL,
  `formato_4` int DEFAULT NULL,
  `merceologia` varchar(20) DEFAULT NULL,
  `flag1_prod` int DEFAULT NULL,
  `tenant_id` bigint DEFAULT NULL,
  PRIMARY KEY (`ID`),
  KEY `idx_tenant_id` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

CREATE TABLE IF NOT EXISTS `ingresso_merce` (
  `progressivo_acq` varchar(5) DEFAULT NULL,
  `data_acq` date DEFAULT NULL,
  `documento` varchar(8) DEFAULT NULL,
  `fornitore` varchar(50) DEFAULT NULL,
  `prodotto` varchar(30) DEFAULT NULL,
  `quantita` varchar(6) DEFAULT NULL,
  `residuo` varchar(6) DEFAULT NULL,
  `lotto_chiuso` varchar(2) DEFAULT NULL,
  `id_merc` int NOT NULL,
  `tenant_id` bigint DEFAULT NULL,
  `fornitore_id` bigint DEFAULT NULL,
  KEY `idx_tenant_id` (`tenant_id`),
  KEY `idx_ingresso_merce_fornitore` (`tenant_id`, `fornitore_id`),
  CONSTRAINT `fk_ingresso_merce_fornitore` FOREIGN KEY (`tenant_id`, `fornitore_id`)
    REFERENCES `soggetti` (`tenant_id`, `id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

CREATE TABLE IF NOT EXISTS `progressivi` (
  `prog_acq` int DEFAULT NULL,
  `prog_ven` int DEFAULT NULL,
  `tenant_id` bigint DEFAULT NULL,
  UNIQUE KEY `uq_progressivi_tenant_id` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

-- ---------------------------------------------------------------------------
-- 4. TRACEABILITY TABLES
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `documenti_ingresso` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `data_ingresso` date NOT NULL,
  `numero_ddt` varchar(40) NOT NULL DEFAULT '',
  `fornitore` varchar(120) NOT NULL,
  `fornitore_id` bigint DEFAULT NULL,
  `creato_il` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_documenti_ingresso_tenant_id` (`tenant_id`, `id`),
  KEY `idx_documenti_ingresso_data` (`tenant_id`, `data_ingresso`),
  KEY `idx_documenti_ingresso_fornitore` (`tenant_id`, `fornitore_id`),
  CONSTRAINT `fk_documenti_ingresso_tenant` FOREIGN KEY (`tenant_id`)
    REFERENCES `tenant` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_documenti_ingresso_fornitore` FOREIGN KEY (`tenant_id`, `fornitore_id`)
    REFERENCES `soggetti` (`tenant_id`, `id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `lavorazioni` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `data_lavorazione` date NOT NULL,
  `descrizione` varchar(255) NOT NULL DEFAULT '',
  `operatore_id` int DEFAULT NULL,
  `operatore` varchar(120) DEFAULT NULL,
  `creato_il` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_lavorazioni_tenant_id` (`tenant_id`, `id`),
  KEY `idx_lavorazioni_data` (`tenant_id`, `data_lavorazione`),
  KEY `idx_lavorazioni_operatore` (`operatore_id`),
  CONSTRAINT `fk_lavorazioni_tenant` FOREIGN KEY (`tenant_id`)
    REFERENCES `tenant` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_lavorazioni_operatore` FOREIGN KEY (`operatore_id`)
    REFERENCES `dipendenti` (`ID`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `lotti` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `articolo_id` bigint NOT NULL,
  `tipo_lotto` char(1) NOT NULL,
  `progressivo` int NOT NULL,
  `codice_lotto` varchar(32) NOT NULL,
  `data_creazione` date NOT NULL,
  `quantita_iniziale` decimal(12,3) NOT NULL,
  `quantita_disponibile` decimal(12,3) NOT NULL,
  `unita_misura` varchar(8) NOT NULL,
  `documento_ingresso_id` bigint DEFAULT NULL,
  `lavorazione_id` bigint DEFAULT NULL,
  `attivo` tinyint(1) NOT NULL DEFAULT 1,
  `creato_il` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_lotti_tenant_id` (`tenant_id`, `id`),
  UNIQUE KEY `uq_lotti_tenant_codice` (`tenant_id`, `codice_lotto`),
  UNIQUE KEY `uq_lotti_tenant_tipo_progressivo` (`tenant_id`, `tipo_lotto`, `progressivo`),
  KEY `idx_lotti_tenant_articolo` (`tenant_id`, `articolo_id`),
  KEY `idx_lotti_tenant_disponibilita` (`tenant_id`, `quantita_disponibile`),
  KEY `idx_lotti_tenant_data` (`tenant_id`, `data_creazione`),
  CONSTRAINT `chk_lotti_tipo` CHECK (`tipo_lotto` IN ('A', 'V')),
  CONSTRAINT `chk_lotti_quantita` CHECK (
    `quantita_iniziale` > 0 AND `quantita_disponibile` >= 0
  ),
  CONSTRAINT `fk_lotti_articolo` FOREIGN KEY (`tenant_id`, `articolo_id`)
    REFERENCES `articoli` (`tenant_id`, `id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_lotti_documento_ingresso` FOREIGN KEY (`tenant_id`, `documento_ingresso_id`)
    REFERENCES `documenti_ingresso` (`tenant_id`, `id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_lotti_lavorazione` FOREIGN KEY (`tenant_id`, `lavorazione_id`)
    REFERENCES `lavorazioni` (`tenant_id`, `id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `movimenti_lotto` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `lotto_id` bigint NOT NULL,
  `tipo` varchar(16) NOT NULL,
  `quantita_delta` decimal(12,3) NOT NULL,
  `documento_ingresso_id` bigint DEFAULT NULL,
  `lavorazione_id` bigint DEFAULT NULL,
  `creato_il` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_movimenti_lotto_lotto` (`tenant_id`, `lotto_id`, `id`),
  CONSTRAINT `chk_movimenti_lotto_tipo` CHECK (
    `tipo` IN ('INGRESSO', 'CONSUMO', 'PRODUZIONE', 'RETTIFICA')
  ),
  CONSTRAINT `chk_movimenti_lotto_delta` CHECK (`quantita_delta` <> 0),
  CONSTRAINT `fk_movimenti_lotto_lotto` FOREIGN KEY (`tenant_id`, `lotto_id`)
    REFERENCES `lotti` (`tenant_id`, `id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_movimenti_lotto_documento` FOREIGN KEY (`tenant_id`, `documento_ingresso_id`)
    REFERENCES `documenti_ingresso` (`tenant_id`, `id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_movimenti_lotto_lavorazione` FOREIGN KEY (`tenant_id`, `lavorazione_id`)
    REFERENCES `lavorazioni` (`tenant_id`, `id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `lavorazione_scarto` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `lavorazione_id` bigint NOT NULL,
  `descrizione` varchar(120) NOT NULL,
  `quantita` decimal(12,3) NOT NULL,
  `unita_misura` varchar(8) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_lavorazione_scarto` (`tenant_id`, `lavorazione_id`),
  CONSTRAINT `chk_lavorazione_scarto_quantita` CHECK (`quantita` > 0),
  CONSTRAINT `fk_lavorazione_scarto_lavorazione` FOREIGN KEY (`tenant_id`, `lavorazione_id`)
    REFERENCES `lavorazioni` (`tenant_id`, `id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `righe_ingresso_tracciato` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `documento_ingresso_id` bigint NOT NULL,
  `lotto_id` bigint NOT NULL,
  `quantita` decimal(12,3) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_righe_ingresso_tenant_id` (`tenant_id`, `id`),
  UNIQUE KEY `uq_righe_ingresso_lotto` (`tenant_id`, `lotto_id`),
  CONSTRAINT `chk_righe_ingresso_quantita` CHECK (`quantita` > 0),
  CONSTRAINT `fk_righe_ingresso_documento` FOREIGN KEY (`tenant_id`, `documento_ingresso_id`)
    REFERENCES `documenti_ingresso` (`tenant_id`, `id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_righe_ingresso_lotto` FOREIGN KEY (`tenant_id`, `lotto_id`)
    REFERENCES `lotti` (`tenant_id`, `id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `lavorazione_input` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `lavorazione_id` bigint NOT NULL,
  `lotto_id` bigint NOT NULL,
  `quantita` decimal(12,3) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_lavorazione_input_lotto` (`tenant_id`, `lotto_id`),
  CONSTRAINT `chk_lavorazione_input_quantita` CHECK (`quantita` > 0),
  CONSTRAINT `fk_lavorazione_input_lavorazione` FOREIGN KEY (`tenant_id`, `lavorazione_id`)
    REFERENCES `lavorazioni` (`tenant_id`, `id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_lavorazione_input_lotto` FOREIGN KEY (`tenant_id`, `lotto_id`)
    REFERENCES `lotti` (`tenant_id`, `id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `lavorazione_output` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `lavorazione_id` bigint NOT NULL,
  `articolo_id` bigint NOT NULL,
  `lotto_id` bigint NOT NULL,
  `quantita` decimal(12,3) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_lavorazione_output_lotto` (`tenant_id`, `lotto_id`),
  CONSTRAINT `chk_lavorazione_output_quantita` CHECK (`quantita` > 0),
  CONSTRAINT `fk_lavorazione_output_lavorazione` FOREIGN KEY (`tenant_id`, `lavorazione_id`)
    REFERENCES `lavorazioni` (`tenant_id`, `id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_lavorazione_output_articolo` FOREIGN KEY (`tenant_id`, `articolo_id`)
    REFERENCES `articoli` (`tenant_id`, `id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_lavorazione_output_lotto` FOREIGN KEY (`tenant_id`, `lotto_id`)
    REFERENCES `lotti` (`tenant_id`, `id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ---------------------------------------------------------------------------
-- RESTORE FOREIGN KEY CHECKS
-- ---------------------------------------------------------------------------
SET FOREIGN_KEY_CHECKS=1;
