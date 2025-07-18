-- Initialize PostgreSQL database for Steam Librarian
-- This script runs when the PostgreSQL container starts for the first time

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create additional user if needed (the main user is created by POSTGRES_USER env var)
-- CREATE USER steam_readonly WITH PASSWORD 'readonly_password';

-- Grant permissions
-- GRANT CONNECT ON DATABASE steam_librarian TO steam_readonly;
-- GRANT USAGE ON SCHEMA public TO steam_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO steam_readonly;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO steam_readonly;

-- Create indexes for better performance (GORM will create tables via auto-migration)
-- These will be applied after GORM creates the tables

-- Note: The actual table creation and schema migration is handled by GORM
-- in the Go application. This file is primarily for database initialization,
-- creating additional users, extensions, or initial data.

-- You can add any initial data here, for example:
-- INSERT INTO settings (key, value) VALUES ('app_version', '0.1.0');

-- Set up database configuration
-- ALTER DATABASE steam_librarian SET timezone TO 'UTC';