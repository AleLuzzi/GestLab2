-- One-time migration for an existing development database.
-- Run against the existing schema; do not run after recreating it from init_database.sql.

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
  `attivo` tinyint NOT NULL DEFAULT 1,
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

ALTER TABLE `fornitori`
  ADD COLUMN `soggetto_id` bigint DEFAULT NULL AFTER `tenant_id`,
  ADD UNIQUE KEY `uq_fornitori_tenant_id` (`tenant_id`, `ID`),
  ADD UNIQUE KEY `uq_fornitori_soggetto` (`tenant_id`, `soggetto_id`),
  ADD CONSTRAINT `fk_fornitori_soggetto` FOREIGN KEY (`tenant_id`, `soggetto_id`)
    REFERENCES `soggetti` (`tenant_id`, `id`) ON DELETE RESTRICT;

-- Keep supplier IDs stable in this development database while creating the
-- corresponding shared subjects and supplier roles.
INSERT INTO `soggetti` (`id`, `tenant_id`, `denominazione`)
SELECT `ID`, `tenant_id`, COALESCE(NULLIF(TRIM(`azienda`), ''), CONCAT('Fornitore ', `ID`))
FROM `fornitori`
WHERE `tenant_id` IS NOT NULL;

INSERT INTO `soggetti_ruoli` (`tenant_id`, `soggetto_id`, `ruolo`)
SELECT `tenant_id`, `ID`, 'fornitore'
FROM `fornitori`
WHERE `tenant_id` IS NOT NULL;

UPDATE `fornitori`
SET `soggetto_id` = `ID`
WHERE `tenant_id` IS NOT NULL;

ALTER TABLE `ingresso_merce`
  ADD COLUMN `fornitore_id` bigint DEFAULT NULL AFTER `tenant_id`,
  ADD KEY `idx_ingresso_merce_fornitore` (`tenant_id`, `fornitore_id`),
  ADD CONSTRAINT `fk_ingresso_merce_fornitore` FOREIGN KEY (`tenant_id`, `fornitore_id`)
    REFERENCES `soggetti` (`tenant_id`, `id`) ON DELETE RESTRICT;

-- Associate only unambiguous exact-name matches. The existing fornitore value
-- remains the historical display snapshot, including for rows not matched here.
UPDATE `ingresso_merce` AS `im`
JOIN (
  SELECT `tenant_id`, `azienda`, MIN(`soggetto_id`) AS `soggetto_id`
  FROM `fornitori`
  WHERE `tenant_id` IS NOT NULL AND `azienda` IS NOT NULL
  GROUP BY `tenant_id`, `azienda`, BINARY `azienda`
  HAVING COUNT(*) = 1
) AS `f`
  ON `f`.`tenant_id` = `im`.`tenant_id`
 AND BINARY `f`.`azienda` = BINARY `im`.`fornitore`
SET `im`.`fornitore_id` = `f`.`soggetto_id`
WHERE `im`.`fornitore_id` IS NULL;

ALTER TABLE `documenti_ingresso`
  ADD COLUMN `fornitore_id` bigint DEFAULT NULL AFTER `fornitore`,
  ADD KEY `idx_documenti_ingresso_fornitore` (`tenant_id`, `fornitore_id`),
  ADD CONSTRAINT `fk_documenti_ingresso_fornitore` FOREIGN KEY (`tenant_id`, `fornitore_id`)
    REFERENCES `soggetti` (`tenant_id`, `id`) ON DELETE RESTRICT;

UPDATE `documenti_ingresso` AS `di`
JOIN (
  SELECT `tenant_id`, `azienda`, MIN(`soggetto_id`) AS `soggetto_id`
  FROM `fornitori`
  WHERE `tenant_id` IS NOT NULL AND `azienda` IS NOT NULL
  GROUP BY `tenant_id`, `azienda`, BINARY `azienda`
  HAVING COUNT(*) = 1
) AS `f`
  ON `f`.`tenant_id` = `di`.`tenant_id`
 AND BINARY `f`.`azienda` = BINARY `di`.`fornitore`
SET `di`.`fornitore_id` = `f`.`soggetto_id`
WHERE `di`.`fornitore_id` IS NULL;
