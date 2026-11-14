CREATE TABLE IF NOT EXISTS `audit_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `utente_email` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `azione` varchar(20) COLLATE utf8mb4_general_ci NOT NULL,
  `entita` varchar(40) COLLATE utf8mb4_general_ci NOT NULL,
  `entita_id` varchar(64) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `dettaglio` varchar(1000) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `creato_il` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_audit_log_tenant` (`tenant_id`, `id`),
  CONSTRAINT `fk_audit_log_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `tenant` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chk_audit_log_azione` CHECK (`azione` IN ('CANCELLAZIONE', 'RETTIFICA'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
