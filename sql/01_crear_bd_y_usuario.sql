-- =========================================================
-- GenX · 01 — Base de datos y usuario de la aplicación
-- Ejecutar en la VM (servidor activo) como root:
--     sudo mysql < sql/01_crear_bd_y_usuario.sql
-- Cambia la contraseña antes de ejecutarlo.
-- =========================================================

CREATE DATABASE IF NOT EXISTS genx_portal
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- La app corre en la misma VM que MySQL, por eso solo se permite acceso local.
CREATE USER IF NOT EXISTS 'genx_app'@'localhost' IDENTIFIED BY 'Cambia-Esta-Clave-2026';
CREATE USER IF NOT EXISTS 'genx_app'@'127.0.0.1' IDENTIFIED BY 'Cambia-Esta-Clave-2026';

-- Solo manipulación de datos: la app NO puede crear, alterar ni borrar tablas.
-- El modelo físico se administra únicamente con los scripts de esta carpeta.
GRANT SELECT, INSERT, UPDATE, DELETE ON genx_portal.* TO 'genx_app'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON genx_portal.* TO 'genx_app'@'127.0.0.1';

FLUSH PRIVILEGES;
