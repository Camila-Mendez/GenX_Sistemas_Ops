-- Ejecutar como superusuario:  sudo -u postgres psql -f sql/postgresql.sql
-- Crea la base y el usuario de la aplicación. Las tablas las crea `flask --app run init-db`.
CREATE USER genx_app WITH PASSWORD 'cambia-esta-contraseña';
CREATE DATABASE genx_portal OWNER genx_app ENCODING 'UTF8';
GRANT ALL PRIVILEGES ON DATABASE genx_portal TO genx_app;
