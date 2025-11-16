# Security Policy

FAIRy-core is a local-first validation engine intended to run in your own
environment. We take security and responsible disclosure seriously, and we
appreciate researchers and users who help keep the ecosystem safe.

This document explains how to report security issues and what to expect.

---

## Supported versions

FAIRy-core is currently in active early development (pre-1.0). In practice:

- We aim to address security issues affecting the **latest released version**
  and the `main` branch.
- Older releases may not receive security fixes unless there is a compelling
  reason (for example, a widely-used version in the community).

If you rely on a specific version and discover a vulnerability, please mention
the version in your report.

---

## Reporting a vulnerability

If you believe you have found a security issue in FAIRy-core:

1. **Do not** open a public GitHub issue with details of the vulnerability.
2. Instead, please email:

   **hello@datadabra.com**
   Subject: `FAIRy-core security report`

Include as much information as you can to help us understand and reproduce
the issue:

- A short description of the problem
- The version of FAIRy-core you tested
- How you are using FAIRy-core (e.g., local CLI, integrated into another tool)
- Step-by-step reproduction instructions or proof-of-concept (if available)
- Any logs or stack traces that might be relevant

We will acknowledge receipt of your report as soon as we reasonably can.

---

## Coordinated disclosure

We aim to follow a responsible, coordinated disclosure process:

- We will investigate the issue and, where appropriate, prepare a fix.
- Once a fix is available (or a mitigation is documented), we may:
  - Publish a new release, and/or
  - Update documentation with mitigation steps, and/or
  - Open a public issue or changelog entry describing the impact.

If you would like to be publicly credited for the discovery, please tell us
how you would like your name or handle to appear. If you prefer to remain
anonymous, we will respect that.

---

## Scope

This security policy covers:

- The FAIRy-core codebase in this repository (`yuummmer/fairy-core`).
- Any officially maintained packages or distributions derived from it.

It does **not** cover third-party tools you may use alongside FAIRy-core, or
local configuration issues outside of the software itself.

If you are unsure whether something is in scope, feel free to ask in your
initial email; we’re happy to clarify.

---

Thank you for helping improve the security and reliability of FAIRy-core. 🌱
