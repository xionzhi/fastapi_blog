# Project conventions

- Production deployment targets Linux, using Docker Compose behind the existing HTTPS reverse proxy.
- Use English for all interface copy, accessibility labels, confirmations, API errors, CLI prompts, and system emails. Preserve original article content and the blog's established name and branding.
- Do not run frontend production builds or compilation automatically. The user will build manually. Run only necessary, targeted functional checks; do not repeat checks without a relevant change or unresolved failure.
- Administrator email is optional SMTP for password recovery and password-change notifications. Leave delivery disabled until the user configures a provider. Never send live emails during development; mock the transport in tests.
- Follow the reference architecture in `E:/xionzhi/aimax_walmart` and Netflix Dispatch: feature-oriented `models.py`, `service.py`, and `views.py`; typed dependencies; thin application composition; explicit error contracts.
- Use SQLAlchemy 2 ORM mappings for all business database queries and mutations. Keep SQLite-specific connection pragmas and transaction control confined to database infrastructure. Use Alembic for schema evolution.
- Frontend requests belong in `src/api/`, shared state in `src/stores/`, and lifecycle-bound behavior in `src/composables/`. Keep Vue templates and script blocks formatted with Prettier.

- Treat other projects and supplied Ghost databases as design references only. Do not implement data import, schema adoption, or backward compatibility. Initialize a new application database.
