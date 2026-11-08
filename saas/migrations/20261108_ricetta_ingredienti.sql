CREATE TABLE IF NOT EXISTS `ricetta_ingredienti` (
  `tenant_id` bigint NOT NULL,
  `ricetta_id` bigint NOT NULL,
  `articolo_id` bigint NOT NULL,
  `posizione` int unsigned NOT NULL,
  `tipo_quantita` varchar(16) NOT NULL,
  `valore` decimal(12,3) NOT NULL,
  `obbligatorio` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`tenant_id`, `ricetta_id`, `articolo_id`),
  UNIQUE KEY `uq_ricetta_ingredienti_posizione` (`tenant_id`, `ricetta_id`, `posizione`),
  KEY `idx_ricetta_ingredienti_articolo` (`tenant_id`, `articolo_id`),
  CONSTRAINT `fk_ricetta_ingredienti_ricetta` FOREIGN KEY (`tenant_id`, `ricetta_id`)
    REFERENCES `ricette` (`tenant_id`, `id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ricetta_ingredienti_articolo` FOREIGN KEY (`tenant_id`, `articolo_id`)
    REFERENCES `articoli` (`tenant_id`, `id`) ON DELETE RESTRICT,
  CONSTRAINT `chk_ricetta_ingredienti_quantita` CHECK (
    `valore` > 0 AND
    (`tipo_quantita` = 'quantita' OR
     (`tipo_quantita` = 'percentuale' AND `valore` <= 100))
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
