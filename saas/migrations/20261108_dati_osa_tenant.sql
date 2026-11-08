ALTER TABLE `tenant`
  ADD COLUMN `osa_ragione_sociale` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  ADD COLUMN `osa_indirizzo` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  ADD COLUMN `osa_laboratorio` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  ADD COLUMN `osa_partita_iva` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL;
