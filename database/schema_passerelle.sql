-- Base locale de la VM2 "Passerelle" (carrefour_stats_db).
--
-- Contient le bilan agrege de chaque session de simulation : une ligne
-- ouverte au demarrage de la passerelle, completee a son arret avec les
-- statistiques observees. Ecriture rare (deux par session), pilotee par
-- le processus qui gere les connexions clients.
--
-- A executer sur la VM2 : sudo mariadb < schema_passerelle.sql

CREATE DATABASE IF NOT EXISTS carrefour_stats_db;
USE carrefour_stats_db;

CREATE TABLE IF NOT EXISTS session_simulation (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date_debut DATETIME,
    date_fin DATETIME,
    nb_vehicules INT DEFAULT 0,
    nb_cyclistes INT DEFAULT 0,
    nb_pietons INT DEFAULT 0,
    nb_accidents INT DEFAULT 0,
    temps_moyen_urgence FLOAT
);
