# Security Remediation

## Overview

Following the security assessment documented in `docs/findings.md`, the application was updated to address the highest-priority vulnerabilities affecting authentication, credential management, database security, and secure configuration.

The remediation effort focused on application-level vulnerabilities that directly impact the confidentiality, integrity, and availability of the Vulnerability Tracker application. Findings that could not be fully remediated within the scope of this implementation have been documented together with their current status, rationale, and recommended next steps.

---

# Remediation Summary

| Finding ID | Current Status | Remediation Performed | Evidence (Git Changes) | Next Step |
|------------|---------------|-----------------------|------------------------|-----------|
| **VT-SAST-001** Hardcoded application secrets | **Resolved** | Removed hardcoded JWT secret and internal API key from the application. Runtime configuration is now supplied using GitHub Secrets and GitHub Variables through environment variables. Mandatory secrets are validated during application startup. | `app/config.py` now retrieves configuration using `os.getenv()`. `.github/workflows/ci-sast-sca-trivy.yaml` injects `SECRET_KEY`, `ADMIN_API_KEY`, `DATABASE_URL`, `ACCESS_TOKEN_EXPIRE_MINUTES`, and `NOTIFY_SERVICE_URL` from GitHub Secrets and Variables. | None |
| **VT-SAST-002** SQL Injection | **Resolved** | Dynamic SQL construction was replaced with parameterised SQL using SQLAlchemy bound parameters. | `app/database.py` now uses `text()` with named parameter binding instead of Python string interpolation. | None |
| **VT-MAN-001** Insecure JWT validation | **Resolved** | JWT validation now accepts only the configured signing algorithm. Support for the insecure `"none"` algorithm was removed. | `app/auth.py` validates JWTs using `algorithms=[ALGORITHM]`. | None |
| **VT-MAN-002** Sensitive information written to logs | **Resolved** | Authentication logging was updated to remove plaintext passwords while retaining useful operational logging. | `app/main.py` logs usernames only during authentication events. | None |
| **VT-SAST-003** Predictable security token generation | **Resolved** | Temporary share tokens now use Python's cryptographically secure `secrets` module. | `app/main.py` replaces `random.choice()` with `secrets.token_urlsafe(32)`. | None |
| **VT-SCA-001** Vulnerable third-party dependencies | **Partially Resolved** | Multiple direct application dependencies were upgraded to supported versions to reduce exposure to publicly disclosed vulnerabilities. | `requirements.txt` updated with newer versions of `fastapi`, `starlette`, `python-jose`, `cryptography`, `python-multipart`, and supporting packages. | Continue monitoring upstream releases and upgrade remaining transitive dependencies once compatible versions become available. |
| **VT-CTR-001** Container base image vulnerabilities | **Partially Resolved** | The application was migrated to the current supported python:3.11.13-slim-bookworm base image. The Dockerfile was enhanced to update operating system packages (apt-get update && apt-get upgrade) during the image build process, ensuring the latest security patches available from the Debian repositories are included in every build. Automated container vulnerability scanning was also integrated into the CI/CD pipeline using Trivy | Container images are rebuilt and scanned automatically during every GitHub Actions execution. | Continue rebuilding images using newer official Python/Debian base image releases as upstream security updates become available. Remaining findings originate from inherited operating system packages. |
| **VT-IAC-001** Kubernetes deployment hardening recommendations | **Partially Resolved** | Fixed: image pinned by digest, `imagePullPolicy: Always`. The Helm deployment was hardened using Kubernetes security best practices including non-root execution, security contexts, resource limits, probes, and container hardening. | Helm manifests are validated automatically using Checkov during every CI/CD execution. | Implement remaining low-risk hardening recommendations, including explicit high UID assignment, during future infrastructure improvements. |

---

# Evidence of Remediation

The following code changes demonstrate how the highest-risk findings identified during the assessment were remediated.

---

## VT-SAST-001 – Hardcoded Application Secrets

### Original Implementation

Sensitive configuration values were embedded directly within the application source code.

```python
DATABASE_URL = "sqlite:///./vulntracker.db"

SECRET_KEY = "v3ry-s3cr3t-jwt-k3y-do-not-share"

DB_USER = "vulntracker_app"
DB_PASSWORD = "Tr@cker2024!"

ADMIN_API_KEY = "sk-vt-prod-8f3a2b1c9d4e5f6a7b8c9d0e1f2a3b4c"
```

### Updated Implementation

Configuration is now supplied through environment variables.

```python
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./vulntracker.db"
)

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is required.")

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")

if not ADMIN_API_KEY:
    raise RuntimeError("ADMIN_API_KEY environment variable is required.")
```

### CI/CD Integration

The GitHub Actions workflow injects runtime configuration from GitHub Secrets and Variables.

```yaml
env:
  SECRET_KEY: ${{ secrets.SECRET_KEY }}
  ADMIN_API_KEY: ${{ secrets.ADMIN_API_KEY }}

  DATABASE_URL: ${{ vars.DATABASE_URL }}
  ACCESS_TOKEN_EXPIRE_MINUTES: ${{ vars.ACCESS_TOKEN_EXPIRE_MINUTES }}
  NOTIFY_SERVICE_URL: ${{ vars.NOTIFY_SERVICE_URL }}
```

**Modified Files**

- `app/config.py`
- `.github/workflows/ci-sast-sca-trivy.yaml`

---

## VT-SAST-002 – SQL Injection

### Original Implementation

User-controlled input was directly incorporated into SQL statements.

```python
sql = (
    f"SELECT id, title, description ..."
    f"WHERE title LIKE '%{query}%'
    OR description LIKE '%{query}%'
    OR cve_id LIKE '%{query}%'"
)

result = db.execute(text(sql))
```

### Updated Implementation

The query now uses parameter binding.

```python
sql = text(
    "SELECT id, title, description, severity, status, cve_id, "
    "affected_component, owner_id, created_at "
    "FROM scan_results "
    "WHERE title LIKE :q "
    "OR description LIKE :q "
    "OR cve_id LIKE :q"
)

result = db.execute(sql, {"q": f"%{query}%"})
```

Parameterized queries ensure user input is treated as data rather than executable SQL.

**Modified File**

- `app/database.py`

---

## VT-MAN-001 – Insecure JWT Validation

### Original Implementation

JWT validation accepted both the configured signing algorithm and the insecure `"none"` algorithm.

```python
payload = jwt.decode(
    token,
    SECRET_KEY,
    algorithms=[ALGORITHM, "none"]
)
```

### Updated Implementation

Only the approved signing algorithm is accepted.

```python
payload = jwt.decode(
    token,
    SECRET_KEY,
    algorithms=[ALGORITHM]
)
```

**Modified File**

- `app/auth.py`

---

## VT-MAN-002 – Sensitive Information Written to Logs

### Original Implementation

Authentication logs contained plaintext passwords.

```python
logger.info(
    "Login attempt — username: %s password: %s",
    payload.username,
    payload.password
)
```

```python
logger.warning(
    "Failed login — username: '%s' password: '%s'",
    payload.username,
    payload.password
)
```

### Updated Implementation

Passwords are no longer written to application logs.

```python
logger.info(
    "Login attempt — username: %s",
    payload.username
)
```

```python
logger.warning(
    "Failed login — username: '%s'",
    payload.username
)
```

Only operationally useful information is retained for troubleshooting and auditing.

**Modified File**

- `app/main.py`

---

## VT-SAST-003 – Predictable Security Token Generation

### Original Implementation

Temporary share tokens were generated using Python's pseudo-random number generator.

```python
token = "".join(
    random.choice(
        string.ascii_letters + string.digits
    )
    for _ in range(32)
)
```

### Updated Implementation

The application now generates cryptographically secure tokens.

```python
token = secrets.token_urlsafe(32)
```

Python's `secrets` module is specifically designed for security-sensitive token generation.

**Modified File**

- `app/main.py`

---

## VT-SCA-001 – Dependency Vulnerabilities

### Original Implementation

Several application dependencies were running outdated versions.

```text
python-jose==3.3.0
cryptography==38.0.1
python-multipart==0.0.6
fastapi==0.104.1
```

### Updated Implementation

Dependencies were upgraded to newer supported versions.

```text
fastapi==0.115.12
starlette==0.46.2
python-jose==3.4.0
cryptography==46.0.3
python-multipart==0.0.22
```

Additional dependency upgrades were performed as newer compatible versions became available.

**Modified File**

- `requirements.txt`

---

# CI/CD Security Improvements

Security validation was integrated directly into the GitHub Actions pipeline to ensure every code change is automatically assessed before deployment.

The pipeline now performs:

- Unit Testing
- Static Application Security Testing (Bandit)
- Software Composition Analysis (pip-audit)
- Docker Image Build
- Container Image Security Scanning (Trivy)
- Docker Image Publishing
- Helm Template Rendering
- Infrastructure as Code Security Scanning (Checkov)
- Security Report Artifact Generation

All security reports are automatically archived as GitHub Actions artifacts to provide traceability and support future security reviews.

---

##### RESIDUAL SECURITY issues

The highest-risk application vulnerabilities identified during the assessment have been remediated through code changes. The remaining findings primarily relate to accepted operational risks, third-party software, or infrastructure components outside the application's direct control.

The remaining items are summarised below.

### Static Application Security Testing (Bandit)

The remaining SAST findings are primarily low-priority secure coding recommendations rather than exploitable application vulnerabilities.

Most of the outstanding findings relate to Bandit's **B101** rule, which flags the use of Python `assert` statements. These assertions are predominantly located within the unit test suite and are used to validate expected application behaviour during testing. Since the test code is not deployed as part of the production application, these findings were assessed as low business risk and have not been removed.

A small number of remaining Bandit findings relate to conservative pattern matching (for example, potential hardcoded strings) where manual review determined that they do not expose sensitive production credentials.

---

### Software Composition Analysis (pip-audit)

Although several vulnerable packages were upgraded, a small number of dependency advisories remain.

These findings primarily affect **transitive dependencies** inherited from third-party libraries rather than packages directly selected by the application. Upgrading or replacing these libraries without compatibility testing may introduce functional regressions.

Examples include:

- **`ecdsa==0.19.2` (PYSEC-2026-1325)** — No patched version is currently available from the upstream maintainers. The risk has been accepted temporarily and will be monitored through scheduled Software Composition Analysis (SCA) scans.
- Additional advisories originate from dependency chains where remediation depends on upstream projects releasing compatible updates.

As a result, dependency vulnerability counts cannot realistically be reduced to zero while maintaining application stability. Future dependency upgrades should continue to balance security improvements with application compatibility and regression testing.

---

### Container Security (Trivy)

The remaining container vulnerabilities are associated primarily with operating system packages inherited from the official `python:3.11.13-slim-bookworm` base image.

To minimise this risk, the Dockerfile was updated to perform operating system package updates during the image build process (`apt-get update` and `apt-get upgrade`). This ensures that the latest security patches available from the Debian repositories are included every time a new container image is built.

# ------------------------------------------------------
# Patch OS Packages (Trivy: libssl3, libgnutls30 CVEs)
# ------------------------------------------------------
RUN apt-get update && \
    apt-get upgrade -y --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


The project continues to use the official `python:3.11.13-slim-bookworm` image because it provides:

- A stable and production-ready Python runtime.
- Long-term support through Debian Bookworm.
- Broad compatibility with the application's Python dependencies.
- A smaller attack surface compared with the full Python image.

Some operating system vulnerabilities remain because Debian has not yet published patched versions of the affected packages. These findings cannot be resolved within the application repository itself and will naturally reduce as newer Debian security updates become available and the container image is rebuilt.

---

### Kubernetes Security (Checkov)

The Helm deployment manifests satisfy the majority of Kubernetes security best practices following infrastructure hardening.

The remaining Checkov findings relate to defence-in-depth recommendations, such as explicitly configuring a higher non-root user ID for the running container. Since the application already executes as a non-root user with privilege escalation disabled and additional container security controls enabled, these findings represent further hardening opportunities rather than immediately exploitable vulnerabilities.

These recommendations are planned for future infrastructure improvements.

---

# Conclusion

The remediation activities prioritised vulnerabilities with the greatest potential business impact, particularly those affecting authentication, credential management, database security, and application configuration.

The implemented changes demonstrate a shift-left DevSecOps approach by combining secure coding practices with automated security validation in the CI/CD pipeline. The remaining findings have been documented transparently together with their current status and recommended future actions, providing a clear roadmap for continued security improvement.