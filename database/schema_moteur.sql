-- Base locale de la VM1 "Simulation" (carrefour_moteur_db).
--
-- Contient les donnees produites tick par tick par le moteur : chaque
-- usager qui entre et sort du carrefour, et les evenements associes.
-- Ces ecritures sont frequentes, d'ou la colocalisation de la base avec
-- le processus qui les produit.
--
-- A executer sur la VM1 : sudo mariadb < schema_moteur.sql

CREATE DATABASE IF NOT EXISTS carrefour_moteur_db;
USE carrefour_moteur_db;

CREATE TABLE IF NOT EXISTS usager (
    id INT PRIMARY KEY,
    type_usager VARCHAR(30) NOT NULL,        -- vehicule_normal, vehicule_urgence, vehicule_autonome, cycliste, pieton
    direction_origine CHAR(1),               -- N, S, E, W
    heure_entree DATETIME,
    heure_sortie DATETIME,
    temps_parcours FLOAT
);

CREATE TABLE IF NOT EXISTS evenement (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usager_id INT,
    type_evenement ENUM('passage', 'accident', 'attente_feu') NOT NULL,
    horodatage DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usager_id) REFERENCES usager(id)
);
