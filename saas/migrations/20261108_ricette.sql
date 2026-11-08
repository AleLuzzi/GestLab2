CREATE TABLE IF NOT EXISTS `ricette` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `nome` varchar(120) NOT NULL,
  `articolo_id` bigint NOT NULL,
  `resa_attesa` decimal(12,3) NOT NULL,
  `scarto_atteso` decimal(12,3) NOT NULL DEFAULT 0.000,
  `attiva` tinyint(1) NOT NULL DEFAULT 1,
  `creata_il` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_ricette_tenant_id` (`tenant_id`, `id`),
  UNIQUE KEY `uq_ricette_tenant_nome` (`tenant_id`, `nome`),
  KEY `idx_ricette_articolo` (`tenant_id`, `articolo_id`),
  CONSTRAINT `fk_ricette_tenant` FOREIGN KEY (`tenant_id`)
    REFERENCES `tenant` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ricette_articolo` FOREIGN KEY (`tenant_id`, `articolo_id`)
    REFERENCES `articoli` (`tenant_id`, `id`) ON DELETE RESTRICT,
  CONSTRAINT `chk_ricette_quantita` CHECK (`resa_attesa` > 0 AND `scarto_atteso` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
