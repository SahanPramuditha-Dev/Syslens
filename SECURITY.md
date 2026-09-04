# Security Policy

## Supported Versions

Security fixes are applied to the latest maintained SysLens release and the current default branch.

## Reporting a Vulnerability

Please do **not** open a public issue for vulnerabilities involving command execution, local file access, dashboard exposure, dependency compromise, or sensitive system telemetry.

Use GitHub's private security advisory flow for this repository when available, or contact the maintainer privately through the contact information on the GitHub profile.

Include a concise description, affected version, reproduction steps, expected impact, and any mitigation you have identified. Remove hostnames, IP addresses, usernames, tokens, or other sensitive machine information from screenshots and logs before sharing them.

## Scope

Security-relevant areas include the CLI, FastAPI/WebSocket dashboard, plugin loading, exported reports, local telemetry collection, and third-party dependencies.
