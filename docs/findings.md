# Security Findings

## Overview

A security assessment was performed against the Vulnerability Tracker application using multiple security analysis techniques covering application code, third-party dependencies, container images, Kubernetes deployment manifests, and manual secure code review.

The assessment used the following tools:

- Bandit (Static Application Security Testing)
- pip-audit (Software Composition Analysis)
- Trivy (Container Image Security)
- Checkov (Infrastructure as Code Security)
- Manual Code Review

The findings below are grouped by assessment type rather than scanner output. Severity has been assessed based on the potential business impact to the Vulnerability Tracker application.

---

# 1. Static Application Security Testing (SAST)

**Tool:** Bandit

| ID | Finding | Severity (Assessment) | Business Impact | Location |
|----|----------|----------------------|-----------------|----------|
| VT-SAST-001 | Hardcoded application secrets | **Critical** – Credentials embedded in source code undermine the application's trust model and could allow attackers to forge authentication tokens or impersonate internal services. | Exposure of JWT signing keys or API credentials could lead to complete compromise of authenticated functionality and unauthorized access to vulnerability reports. | Starter code |
| VT-SAST-002 | SQL Injection in search functionality | **Critical** – User input was incorporated into SQL queries without proper parameterisation. | Attackers could retrieve, modify or delete stored vulnerability records, affecting both confidentiality and integrity of the application's data. | Starter code |
| VT-SAST-003 | Predictable security token generation | **Medium** – Security-sensitive tokens were generated using a predictable pseudo-random generator rather than a cryptographically secure source. | Predictable share tokens may allow unauthorized users to gain access to shared vulnerability reports. | Starter code |

> **Note:** Bandit also reported several lower-priority secure coding recommendations (for example, assertions and remaining hardcoded string detections). These findings generally represent coding best practices rather than immediately exploitable vulnerabilities and therefore received lower business priority during risk assessment.

---

# 2. Manual Secure Code Review

**Detection Method:** Manual Review

| ID | Finding | Severity (Assessment) | Business Impact | Location |
|----|----------|----------------------|-----------------|----------|
| VT-MAN-001 | Insecure JWT validation | **High** – Authentication accepted insecure JWT validation behaviour, weakening authentication integrity. | Authentication bypass could expose vulnerability reports and administrative functionality to unauthorized users. | Starter code |
| VT-MAN-002 | Sensitive information written to application logs | **High** – Authentication logs contained user credentials. | Compromise of application logs could expose user passwords and facilitate account compromise, particularly where passwords are reused. | Starter code |

---

# 3. Software Composition Analysis (SCA)

**Tool:** pip-audit

| ID | Finding | Severity (Assessment) | Business Impact | Location |
|----|----------|----------------------|-----------------|----------|
| VT-SCA-001 | Vulnerable third-party Python dependencies | **High** – The application relies on external packages with publicly disclosed security vulnerabilities. | Exploitation depends on affected code paths, but vulnerable dependencies increase the overall attack surface and may expose the application to denial-of-service, authentication, or cryptographic weaknesses inherited from third-party software. | Starter code |

---

# 4. Container Security Assessment

**Tool:** Trivy (Container Image Scan)

| ID | Finding | Severity (Assessment) | Business Impact | Location |
|----|----------|----------------------|-----------------|----------|
| VT-CTR-001 | Operating system package vulnerabilities inherited from the container base image | **High** – The official Python base image contains operating system packages with known vulnerabilities. | While these packages are not directly exposed through application functionality, they increase post-compromise risk if an attacker gains code execution inside the container. | Container Infrastructure |

---

# 5. Infrastructure as Code Security Assessment

**Tool:** Checkov

| ID | Finding | Severity (Assessment) | Business Impact | Location |
|----|----------|----------------------|-----------------|----------|
| VT-IAC-001 | Kubernetes deployment hardening recommendations | **Low** – The Helm chart contains deployment configurations that could be further aligned with Kubernetes security best practices. | These findings primarily represent defence-in-depth improvements that reduce the impact of future exploitation rather than directly exploitable application vulnerabilities. | Helm Chart (New Feature) |

---

# Overall Risk Assessment

The assessment identified the greatest business risk within the application layer, particularly around authentication, credential management, and database interaction. These findings directly affect the confidentiality and integrity of vulnerability assessment data and therefore received the highest priority.

The remaining findings relate primarily to third-party dependencies, container operating system packages, and Kubernetes deployment hardening. These represent important operational security considerations but generally require upstream package updates or infrastructure hardening rather than changes to the application's core business logic.