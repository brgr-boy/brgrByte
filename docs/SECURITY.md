# Security

- Set unique, randomly generated administrator, database, and JWT signing secrets before starting Compose. Never commit `.env` or use example placeholders outside local setup.
- Passwords use Argon2 hashing. API access tokens are signed with HS256, expire after a configurable interval, and are kept in browser memory only (a page refresh requires sign-in again).
- Inventory APIs require authentication. The viewer role cannot create sites; role enforcement is server-side.
- Site creation writes an actor-attributed audit event in the same database transaction as the change.
- PostgreSQL is private to the Compose network. The API process runs as a non-root container user.
- Configure exact browser origins using `NETWORKPATH_CORS_ORIGINS`. Put production traffic behind TLS termination and restrict management port access.
- The agent execution API is not implemented. Future agent work must use allow-listed engine configurations and safe argument-vector subprocess execution; it must not accept arbitrary shell commands.
- Existing administrator passwords are not overwritten on startup. Rotate credentials through a future dedicated administrative operation; until then, bootstrap password changes apply only to a newly created account.

This foundation does not yet provide user self-service, rate limiting, comprehensive audit coverage for authentication and future test operations, TLS certificate automation, agent credential rotation, or production-grade account recovery.
