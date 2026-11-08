-- Schéma de la base du projet "Carrefour intelligent"
-- À exécuter sur la VM Serveur : mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS carrefour_db;
USE carrefour_db;

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
