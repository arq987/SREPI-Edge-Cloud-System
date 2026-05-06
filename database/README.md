# Database migrations

This folder stores SQL Server migrations for the project.

## Structure

- `migrations/` contains versioned scripts in the format `V###__descripcion.sql`.
- `schema_version` is the table that tracks applied migrations.

## How to apply

1. Connect to the target Azure SQL database.
2. Run the migration scripts in order.

## Notes

- Never edit a migration that has already been applied.
- Create a new migration for each change.
