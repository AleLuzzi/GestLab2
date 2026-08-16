-- ------------------------------------------------
-- GestLab - Struttura del database 'data'
-- Generato automaticamente il 2026-08-16T15:46:03.858858
-- Contiene SOLO lo schema (CREATE TABLE), nessun dato.
-- ------------------------------------------------

-- Tabella: classi
CREATE TABLE `classi` (
  `Id` int DEFAULT NULL,
  `classe` varchar(14) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

-- Tabella: dipendenti
CREATE TABLE `dipendenti` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(25) DEFAULT NULL,
  `cognome` varchar(25) DEFAULT NULL,
  `reparto` int DEFAULT NULL,
  `email` varchar(50) DEFAULT NULL,
  `tenant_id` bigint DEFAULT NULL,
  PRIMARY KEY (`ID`),
  KEY `idx_tenant_id` (`tenant_id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb3;

-- Tabella: dispositivi_stampa
CREATE TABLE `dispositivi_stampa` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `nome` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `token` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `stampante_dymo` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `stampante_termica` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `ultimo_heartbeat` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`),
  KEY `fk_dispositivi_tenant` (`tenant_id`),
  CONSTRAINT `fk_dispositivi_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `tenant` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Tabella: fornitori
CREATE TABLE `fornitori` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `azienda` varchar(50) DEFAULT NULL,
  `flag1_ing_merce` int DEFAULT NULL,
  `flag2_inventario` int NOT NULL,
  `tenant_id` bigint DEFAULT NULL,
  PRIMARY KEY (`ID`),
  KEY `idx_tenant_id` (`tenant_id`)
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb3;

-- Tabella: ingredienti
CREATE TABLE `ingredienti` (
  `settimana` int DEFAULT NULL,
  `prodotto` varchar(30) DEFAULT NULL,
  `quantita` varchar(6) DEFAULT NULL,
  `data_utilizzo` date DEFAULT NULL,
  `cod_ean` char(13) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

-- Tabella: ingredienti_base
CREATE TABLE `ingredienti_base` (
  `Id` int NOT NULL AUTO_INCREMENT,
  `ingrediente_base` varchar(50) DEFAULT NULL,
  `cod_ean` char(13) DEFAULT NULL,
  `flag1_allergene` int DEFAULT NULL,
  `merceologia` varchar(12) DEFAULT NULL,
  PRIMARY KEY (`Id`)
) ENGINE=InnoDB AUTO_INCREMENT=44 DEFAULT CHARSET=utf8mb3;

-- Tabella: ingresso_merce
CREATE TABLE `ingresso_merce` (
  `progressivo_acq` varchar(5) DEFAULT NULL,
  `data_acq` date DEFAULT NULL,
  `documento` varchar(8) DEFAULT NULL,
  `fornitore` varchar(50) DEFAULT NULL,
  `prodotto` varchar(30) DEFAULT NULL,
  `quantita` varchar(6) DEFAULT NULL,
  `residuo` varchar(6) DEFAULT NULL,
  `lotto_chiuso` varchar(2) DEFAULT NULL,
  `id_merc` int NOT NULL,
  `tenant_id` bigint DEFAULT NULL,
  KEY `idx_tenant_id` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

-- Tabella: inventari
CREATE TABLE `inventari` (
  `Id` int NOT NULL AUTO_INCREMENT,
  `data_rilevazione` varchar(10) DEFAULT NULL,
  `prodID` int DEFAULT NULL,
  `mercID` int DEFAULT NULL,
  `peso_rilevato` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`Id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb3;

-- Tabella: lotti_vendita
CREATE TABLE `lotti_vendita` (
  `progressivo_ven` varchar(10) DEFAULT NULL,
  `data_ven` date DEFAULT NULL,
  `lotto_acq` varchar(10) DEFAULT NULL,
  `prodotto` varchar(30) DEFAULT NULL,
  `quantita` varchar(10) DEFAULT NULL,
  `prod_origine` varchar(10) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

-- Tabella: lotti_vendita_cucina
CREATE TABLE `lotti_vendita_cucina` (
  `Id` int NOT NULL AUTO_INCREMENT,
  `progressivo_ven_c` varchar(10) DEFAULT NULL,
  `prodotto` varchar(30) DEFAULT NULL,
  `quantita` varchar(10) DEFAULT NULL,
  `data_prod` date DEFAULT NULL,
  `settimana` int DEFAULT NULL,
  PRIMARY KEY (`Id`)
) ENGINE=InnoDB AUTO_INCREMENT=5456 DEFAULT CHARSET=utf8mb3;

-- Tabella: merceologie
CREATE TABLE `merceologie` (
  `Id` int NOT NULL AUTO_INCREMENT,
  `merceologia` varchar(23) DEFAULT NULL,
  `Id_Reparto` int DEFAULT NULL,
  `flag1_inv` int DEFAULT NULL,
  `flag2_taglio` int DEFAULT NULL,
  `flag3_ing_base` int DEFAULT NULL,
  `tenant_id` bigint DEFAULT NULL,
  PRIMARY KEY (`Id`),
  KEY `Id` (`Id`),
  KEY `Id_2` (`Id`),
  KEY `idx_merceologie_tenant` (`tenant_id`),
  KEY `idx_tenant_id` (`tenant_id`)
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb3;

-- Tabella: merceologie_old
CREATE TABLE `merceologie_old` (
  `Id` int NOT NULL,
  `merceologia` varchar(23) DEFAULT NULL,
  `Id_Reparto` int DEFAULT NULL,
  `flag1_inv` int DEFAULT NULL,
  `flag2_taglio` int DEFAULT NULL,
  `flag3_ing_base` int DEFAULT NULL,
  PRIMARY KEY (`Id`),
  KEY `Id` (`Id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

-- Tabella: print_jobs
CREATE TABLE `print_jobs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint NOT NULL,
  `dispositivo_id` bigint DEFAULT NULL,
  `tipo` varchar(20) COLLATE utf8mb4_general_ci NOT NULL,
  `stato` varchar(20) COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'pending',
  `payload` text COLLATE utf8mb4_general_ci NOT NULL,
  `creato_il` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `stampato_il` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_printjobs_tenant` (`tenant_id`),
  KEY `fk_printjobs_dispositivo` (`dispositivo_id`),
  CONSTRAINT `fk_printjobs_dispositivo` FOREIGN KEY (`dispositivo_id`) REFERENCES `dispositivi_stampa` (`id`),
  CONSTRAINT `fk_printjobs_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `tenant` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Tabella: prodotti
CREATE TABLE `prodotti` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `prodotto` varchar(30) DEFAULT NULL,
  `reparto` varchar(11) DEFAULT NULL,
  `plu` varchar(5) DEFAULT NULL,
  `prezzo1` int DEFAULT NULL,
  `prezzo2` varchar(1) DEFAULT NULL,
  `prezzo3` varchar(1) DEFAULT NULL,
  `prezzo4` varchar(1) DEFAULT NULL,
  `prezzo_straord` varchar(1) DEFAULT NULL,
  `gruppo_merc` varchar(1) DEFAULT NULL,
  `tara` varchar(1) DEFAULT NULL,
  `gg_cons_1` varchar(3) DEFAULT NULL,
  `gg_cons_2` varchar(1) DEFAULT NULL,
  `ean` varchar(7) DEFAULT NULL,
  `testo_agg_1` int DEFAULT NULL,
  `testo_agg_2` int DEFAULT NULL,
  `testo_agg_3` int DEFAULT NULL,
  `testo_agg_4` int DEFAULT NULL,
  `pz_x_scatola` int DEFAULT NULL,
  `peso_fisso` int DEFAULT NULL,
  `num_offerta` int DEFAULT NULL,
  `art_in_pubblic` int DEFAULT NULL,
  `sovrascritt_prezzo` int DEFAULT NULL,
  `stile_tracc` int DEFAULT NULL,
  `rich_stm_traccia` int DEFAULT NULL,
  `riga_1` varchar(55) DEFAULT NULL,
  `riga_2` varchar(41) DEFAULT NULL,
  `riga_3` varchar(32) DEFAULT NULL,
  `riga_4` varchar(5) DEFAULT NULL,
  `formato_1` int DEFAULT NULL,
  `formato_2` int DEFAULT NULL,
  `formato_3` int DEFAULT NULL,
  `formato_4` int DEFAULT NULL,
  `merceologia` varchar(20) DEFAULT NULL,
  `flag1_prod` int DEFAULT NULL,
  `tenant_id` bigint DEFAULT NULL,
  PRIMARY KEY (`ID`),
  KEY `idx_tenant_id` (`tenant_id`)
) ENGINE=InnoDB AUTO_INCREMENT=119 DEFAULT CHARSET=utf8mb3;

-- Tabella: progressivi
CREATE TABLE `progressivi` (
  `prog_acq` int DEFAULT NULL,
  `prog_ven` int DEFAULT NULL,
  `tenant_id` bigint DEFAULT NULL,
  KEY `idx_tenant_id` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

-- Tabella: reparti
CREATE TABLE `reparti` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `reparto` varchar(15) DEFAULT NULL,
  `flag1_dip` int DEFAULT NULL,
  `flag2_prod` int DEFAULT NULL,
  `tenant_id` bigint DEFAULT NULL,
  PRIMARY KEY (`ID`),
  KEY `idx_tenant_id` (`tenant_id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb3;

-- Tabella: tagli
CREATE TABLE `tagli` (
  `Id` int NOT NULL AUTO_INCREMENT,
  `taglio` varchar(40) DEFAULT NULL,
  `Id_Merceologia` int DEFAULT NULL,
  `tenant_id` bigint DEFAULT NULL,
  PRIMARY KEY (`Id`),
  KEY `idx_tenant_id` (`tenant_id`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8mb3;

-- Tabella: tenant
CREATE TABLE `tenant` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `nome` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `piano` varchar(50) COLLATE utf8mb4_general_ci DEFAULT 'basic',
  `attivo` tinyint(1) DEFAULT '1',
  `creato_il` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Tabella: utenti
CREATE TABLE `utenti` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tenant_id` bigint DEFAULT NULL,
  `email` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `ruolo` varchar(20) COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'operatore',
  `attivo` tinyint(1) DEFAULT '1',
  `creato_il` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  KEY `fk_utenti_tenant` (`tenant_id`),
  CONSTRAINT `fk_utenti_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `tenant` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
