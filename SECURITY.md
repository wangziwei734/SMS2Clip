# Security policy

## Supported versions

The latest published release is supported with security fixes. Older releases may not receive updates.

## Reporting a vulnerability

Do not open a public issue for security-sensitive reports. Use GitHub's private vulnerability reporting:

https://github.com/wangziwei734/SMS2Clip/security/advisories/new

Please include:

- affected SMS2Clip version;
- Windows version;
- impact and reproduction steps;
- whether credentials, message history, or clipboard data may have been exposed.

## Security model and data handling

- A public ntfy topic is effectively a password. Use a long random topic; self-host ntfy with authentication for sensitive use.
- SMS content and verification codes transit the configured ntfy server.
- Access tokens and Basic Auth credentials are stored in `%APPDATA%\SMS2Clip\config.json`.
- Message history is stored as plain text in `%APPDATA%\SMS2Clip\history.json`. The History tab can clear it.
- Application logs intentionally avoid SMS body text, but may contain message IDs and connection status.
- Windows clipboard history or cross-device sync may retain or transmit copied content. Disable those Windows features when appropriate.

## Release binaries

Release executables are currently unsigned. Review the SHA-256 value in the corresponding release and expect Windows SmartScreen to warn on first run.
