# Project conventions

- Production deployment targets Linux with Docker Compose behind an HTTPS reverse proxy.
- Use English for all interface copy, accessibility labels, confirmations, API errors, CLI prompts, and system emails. Preserve original article content and the blog's established name and branding.
- Do not run frontend production builds or compilation automatically. The user will build manually. Run only necessary, targeted functional checks; do not repeat checks without a relevant change or unresolved failure.
- Administrator email is optional SMTP for password recovery and password-change notifications. Leave delivery disabled until the user configures a provider. Never send live emails during development; mock the transport in tests.
- Organize backend features into `models.py`, `service.py`, and `views.py`. Use typed dependencies, thin application composition, and explicit error contracts.
- Use SQLAlchemy 2 ORM mappings for all business database queries and mutations. Keep SQLite-specific connection pragmas and transaction control confined to database infrastructure. Use Alembic for schema evolution.
- Frontend requests belong in `src/api/`, shared state in `src/stores/`, and lifecycle-bound behavior in `src/composables/`. Keep Vue templates and script blocks formatted with Prettier.
- Initialize an application-owned database. Content transfer uses the native JSON format; keep administrator credentials and deployment configuration outside exports.
