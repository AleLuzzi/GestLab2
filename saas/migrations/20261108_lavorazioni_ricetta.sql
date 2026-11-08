ALTER TABLE `lavorazioni`
  ADD COLUMN `ricetta_id` bigint DEFAULT NULL,
  ADD KEY `idx_lavorazioni_ricetta` (`tenant_id`, `ricetta_id`),
  ADD CONSTRAINT `fk_lavorazioni_ricetta` FOREIGN KEY (`tenant_id`, `ricetta_id`)
    REFERENCES `ricette` (`tenant_id`, `id`) ON DELETE RESTRICT;
