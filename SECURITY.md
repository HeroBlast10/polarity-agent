# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in **Polarity Agent**, please report it
**responsibly** by emailing:

> **xfwang@link.cuhk.edu.hk**

**Do NOT open a public GitHub issue for security vulnerabilities.**

### What to include

- A clear description of the vulnerability.
- Steps to reproduce or a proof-of-concept.
- The potential impact.

### Response timeline

| Stage               | Target          |
| ------------------- | --------------- |
| Acknowledgement     | within 48 hours |
| Initial assessment  | within 7 days   |
| Fix / advisory      | within 30 days  |

## Scope

This project is a **client-side library / CLI tool**. It does not operate any
hosted services. The security scope is therefore limited to:

- Dependency supply-chain attacks.
- Code injection via malicious Persona Packs.
- Credential leakage through misconfigured LLM provider settings.

If you believe a Persona Pack distributed by a third party violates our
[Acceptable Use Policy](AUP.md), please report it using the same email above.

## Acknowledgements

We appreciate all security researchers who help keep Polarity Agent safe.
Contributors will be credited in release notes (unless they prefer anonymity).
