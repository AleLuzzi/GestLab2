-- Aggiunge il TMC senza modificare le date di scadenza gia' registrate.
ALTER TABLE `lotti`
  ADD COLUMN `data_tmc` DATE NULL AFTER `data_scadenza`,
  ADD CONSTRAINT `chk_lotti_data_scadenza_tmc`
    CHECK (`data_scadenza` IS NULL OR `data_tmc` IS NULL);
