CREATE TABLE IF NOT EXISTS `vendite` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `numero` bigint unsigned NOT NULL,
  `data_vendita` datetime NOT NULL,
  `cliente_id` bigint DEFAULT NULL,
  `tipo_documento` varchar(16) NOT NULL,
  `creato_il` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_vendite_tenant_id` (`tenant_id`, `id`),
  UNIQUE KEY `uq_vendite_tenant_numero` (`tenant_id`, `numero`),
  KEY `idx_vendite_tenant_data` (`tenant_id`, `data_vendita`),
  KEY `idx_vendite_tenant_cliente` (`tenant_id`, `cliente_id`),
  CONSTRAINT `chk_vendite_tipo_documento`
    CHECK (`tipo_documento` IN ('DDT', 'RICEVUTA')),
  CONSTRAINT `fk_vendite_tenant` FOREIGN KEY (`tenant_id`)
    REFERENCES `tenant` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_vendite_cliente` FOREIGN KEY (`tenant_id`, `cliente_id`)
    REFERENCES `soggetti` (`tenant_id`, `id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `righe_vendita` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `vendita_id` bigint NOT NULL,
  `lotto_id` bigint NOT NULL,
  `articolo_id` bigint NOT NULL,
  `quantita` decimal(12,3) NOT NULL,
  `unita_misura` varchar(8) NOT NULL,
  `prezzo_unitario` decimal(12,4) NOT NULL,
  `iva_percentuale` decimal(5,2) NOT NULL DEFAULT 0.00,
  PRIMARY KEY (`id`),
  KEY `idx_righe_vendita_documento` (`tenant_id`, `vendita_id`, `id`),
  KEY `idx_righe_vendita_lotto` (`tenant_id`, `lotto_id`),
  CONSTRAINT `chk_righe_vendita_quantita_prezzo_iva`
    CHECK (
      `quantita` > 0 AND `prezzo_unitario` >= 0
      AND `iva_percentuale` >= 0 AND `iva_percentuale` <= 100
    ),
  CONSTRAINT `fk_righe_vendita_documento` FOREIGN KEY (`tenant_id`, `vendita_id`)
    REFERENCES `vendite` (`tenant_id`, `id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_righe_vendita_lotto` FOREIGN KEY (`tenant_id`, `lotto_id`)
    REFERENCES `lotti` (`tenant_id`, `id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_righe_vendita_articolo` FOREIGN KEY (`tenant_id`, `articolo_id`)
    REFERENCES `articoli` (`tenant_id`, `id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
