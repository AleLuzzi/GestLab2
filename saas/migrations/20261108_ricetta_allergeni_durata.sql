ALTER TABLE `ricette`
  ADD COLUMN `giorni_vita` int unsigned DEFAULT NULL,
  ADD COLUMN `istruzioni_conservazione` varchar(1000) DEFAULT NULL,
  ADD COLUMN `istruzioni_cottura` varchar(1000) DEFAULT NULL,
  ADD CONSTRAINT `chk_ricette_giorni_vita`
    CHECK (`giorni_vita` IS NULL OR `giorni_vita` > 0);

CREATE TABLE IF NOT EXISTS `ricetta_allergeni` (
  `tenant_id` bigint NOT NULL,
  `ricetta_id` bigint NOT NULL,
  `codice` varchar(32) NOT NULL,
  PRIMARY KEY (`tenant_id`, `ricetta_id`, `codice`),
  CONSTRAINT `fk_ricetta_allergeni_ricetta` FOREIGN KEY (`tenant_id`, `ricetta_id`)
    REFERENCES `ricette` (`tenant_id`, `id`) ON DELETE CASCADE,
  CONSTRAINT `chk_ricetta_allergeni_codice` CHECK (`codice` IN (
    'glutine', 'crostacei', 'uova', 'pesce', 'arachidi', 'soia', 'latte',
    'frutta_a_guscio', 'sedano', 'senape', 'sesamo', 'solfiti', 'lupini',
    'molluschi'
  ))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
