ALTER TABLE `movimenti_lotto`
  ADD COLUMN `motivo` varchar(16) DEFAULT NULL AFTER `quantita_delta`;
