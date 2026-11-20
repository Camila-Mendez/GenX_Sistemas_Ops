-- Ejecutar como root:  sudo mysql < sql/mysql.sql
-- Crea la base y el usuario de la aplicación. Las tablas las crea `flask --app run init-db`.
CREATE DATABASE IF NOT EXISTS genx_portal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- '%' permite conectarse desde ambos servidores; restrínjalo a la subred interna si es posible (p. ej. '10.0.0.%').
CREATE USER IF NOT EXISTS 'genx_app'@'%' IDENTIFIED BY 'cambia-esta-contraseña';
GRANT ALL PRIVILEGES ON genx_portal.* TO 'genx_app'@'%';
FLUSH PRIVILEGES;
