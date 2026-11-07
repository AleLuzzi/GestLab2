-- Aggiunge i metadati di lotto richiesti per la Fase A del piano vendibile.
-- Consentono di registrare scadenza, origine e lotto fornitore per i lotti A/V.

ALTER TABLE `lotti`
  ADD COLUMN `data_scadenza` DATE NULL AFTER `data_creazione`,
  ADD COLUMN `lotto_fornitore` VARCHAR(64) NULL AFTER `data_scadenza`,
  ADD COLUMN `origine` VARCHAR(255) NULL AFTER `lotto_fornitore`,
  ADD COLUMN `temperatura_ingresso` DECIMAL(6,2) NULL AFTER `origine`;
