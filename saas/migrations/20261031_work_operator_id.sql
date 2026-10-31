-- Store the selected employee ID while retaining the operator name snapshot
-- for existing detail views and records.
ALTER TABLE `lavorazioni`
  ADD COLUMN `operatore_id` int DEFAULT NULL AFTER `descrizione`,
  ADD KEY `idx_lavorazioni_operatore` (`operatore_id`),
  ADD CONSTRAINT `fk_lavorazioni_operatore` FOREIGN KEY (`operatore_id`)
    REFERENCES `dipendenti` (`ID`) ON DELETE SET NULL;
