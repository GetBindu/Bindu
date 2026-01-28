-- Create separate databases for Hydra and Kratos
CREATE DATABASE hydra;
CREATE DATABASE kratos;

-- Grant all privileges to postgres user
GRANT ALL PRIVILEGES ON DATABASE hydra TO postgres;
GRANT ALL PRIVILEGES ON DATABASE kratos TO postgres;

-- Optional: Create extensions if needed
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
