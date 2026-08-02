# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **DO NOT** open a public GitHub issue.
2. Email or DM the maintainer directly.
3. Include: description, steps to reproduce, potential impact.

You should receive a response within 72 hours.

## What we consider a security issue

- Exposed credentials or subscription URLs in logs
- Remote code execution via crafted config
- Man-in-the-middle on gRPC/stats channel
- Privilege escalation via Kill Switch / firewall rules
- Data leakage from storage.json (plaintext secrets)

## Scope

This project uses **Xray-core** as an external binary. Vulnerabilities in Xray itself should be reported to the [Xray-core](https://github.com/XTLS/Xray-core) project.
