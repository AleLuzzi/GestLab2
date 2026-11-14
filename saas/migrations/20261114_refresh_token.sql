CREATE TABLE IF NOT EXISTS `refresh_token` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `utente_id` bigint NOT NULL,
  `token_hash` char(64) COLLATE utf8mb4_general_ci NOT NULL,
  `famiglia` char(36) COLLATE utf8mb4_general_ci NOT NULL,
  `scade_il` datetime NOT NULL,
  `revocato_il` datetime DEFAULT NULL,
  `creato_il` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_refresh_token_hash` (`token_hash`),
  KEY `idx_refresh_token_famiglia` (`famiglia`),
  KEY `fk_refresh_token_utente` (`utente_id`),
  CONSTRAINT `fk_refresh_token_utente` FOREIGN KEY (`utente_id`) REFERENCES `utenti` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
