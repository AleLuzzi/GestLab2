-- Aggiorna il controllo del tipo movimento per includere la vendita interna.
-- Necessario per il flusso vendite interne senza rompere il saldo dei lotti.

ALTER TABLE `movimenti_lotto`
  DROP CHECK `chk_movimenti_lotto_tipo`;

ALTER TABLE `movimenti_lotto`
  ADD CONSTRAINT `chk_movimenti_lotto_tipo`
  CHECK (`tipo` IN ('INGRESSO', 'CONSUMO', 'PRODUZIONE', 'RETTIFICA', 'VENDITA'));
