# Security and privacy

The default server listens on localhost and uses a per-process request token plus Host validation. It is designed for a single local user; profiles are not authenticated accounts. Docker Compose publishes only to 127.0.0.1. Do not expose this prototype publicly without authentication, HTTPS and access controls.

API credentials come from environment variables and stay on the server. Enabling model interpretation sends the relevant question, computed results and birth information to the configured provider. Saved profiles and reports are plaintext SQLite files with restrictive filesystem permissions. Exported files and backups can contain birth data. Local review notes are excluded from model requests.

Report sensitive issues privately through the repository's GitHub security advisory mechanism when enabled. Otherwise contact the maintainer through the contact information on their GitHub profile; do not post credentials or private birth records in a public issue. No email or private channel is assumed to exist.
