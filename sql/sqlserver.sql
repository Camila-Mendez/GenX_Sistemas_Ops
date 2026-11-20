-- Ejecutar con sqlcmd:  sqlcmd -S localhost -U sa -C -i sql/sqlserver.sql
-- Crea la base y el usuario de la aplicación. Las tablas las crea `flask --app run init-db`.
CREATE DATABASE genx_portal;
GO
CREATE LOGIN genx_app WITH PASSWORD = 'Cambia-Esta-Clave1!';
GO
USE genx_portal;
GO
CREATE USER genx_app FOR LOGIN genx_app;
ALTER ROLE db_owner ADD MEMBER genx_app;
GO
