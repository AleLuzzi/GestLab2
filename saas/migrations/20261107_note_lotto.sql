-- Aggiunge note descrittive facoltative ai lotti, senza attribuire loro valore
-- di certificazione o propagazione automatica ai lotti prodotti.
ALTER TABLE `lotti`
  ADD COLUMN `note_lotto` VARCHAR(500) NULL AFTER `temperatura_ingresso`;
