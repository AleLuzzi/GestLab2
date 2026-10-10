-- Additive migration for the stock traceability model.
-- Existing products, ingress rows and sales lots are intentionally preserved.

CREATE TABLE IF NOT EXISTS `articoli` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `codice` varchar(60) DEFAULT NULL,
  `nome` varchar(120) NOT NULL,
  `categoria` varchar(80) DEFAULT NULL,
  `unita_misura` varchar(8) NOT NULL DEFAULT 'kg',
  `attivo` tinyint NOT NULL DEFAULT 1,
  `creato_il` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_articoli_tenant_id` (`tenant_id`, `id`),
  UNIQUE KEY `uq_articoli_tenant_codice` (`tenant_id`, `codice`),
  KEY `idx_articoli_tenant_nome` (`tenant_id`, `nome`),
  CONSTRAINT `fk_articoli_tenant` FOREIGN KEY (`tenant_id`)
    REFERENCES `tenant` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `documenti_ingresso` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `data_ingresso` date NOT NULL,
  `numero_ddt` varchar(40) NOT NULL DEFAULT '',
  `fornitore` varchar(120) NOT NULL,
  `creato_il` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_documenti_ingresso_tenant_id` (`tenant_id`, `id`),
  KEY `idx_documenti_ingresso_data` (`tenant_id`, `data_ingresso`),
  CONSTRAINT `fk_documenti_ingresso_tenant` FOREIGN KEY (`tenant_id`)
    REFERENCES `tenant` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `lavorazioni` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `data_lavorazione` date NOT NULL,
  `descrizione` varchar(255) NOT NULL DEFAULT '',
  `operatore` varchar(120) DEFAULT NULL,
  `creato_il` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_lavorazioni_tenant_id` (`tenant_id`, `id`),
  KEY `idx_lavorazioni_data` (`tenant_id`, `data_lavorazione`),
  CONSTRAINT `fk_lavorazioni_tenant` FOREIGN KEY (`tenant_id`)
    REFERENCES `tenant` (`id`) ON DELETE CASCADE
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
  `attivo` tinyint NOT NULL DEFAULT 1,
  `creato_il` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_lotti_tenant_id` (`tenant_id`, `id`),
  UNIQUE KEY `uq_lotti_tenant_codice` (`tenant_id`, `codice_lotto`),
  UNIQUE KEY `uq_lotti_tenant_tipo_progressivo` (`tenant_id`, `tipo_lotto`, `progressivo`),
  KEY `idx_lotti_tenant_articolo` (`tenant_id`, `articolo_id`),
  KEY `idx_lotti_tenant_disponibilita` (`tenant_id`, `quantita_disponibile`),
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
