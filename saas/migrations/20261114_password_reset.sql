CREATE TABLE IF NOT EXISTS `password_reset` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `utente_id` bigint NOT NULL,
  `token_hash` char(64) COLLATE utf8mb4_general_ci NOT NULL,
  `scade_il` datetime NOT NULL,
  `usato_il` datetime DEFAULT NULL,
  `creato_il` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_password_reset_token` (`token_hash`),
  KEY `fk_password_reset_utente` (`utente_id`),
  CONSTRAINT `fk_password_reset_utente` FOREIGN KEY (`utente_id`) REFERENCES `utenti` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
