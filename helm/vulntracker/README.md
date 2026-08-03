# vulntracker Helm chart

Deploys the VulnTracker FastAPI API to Kubernetes.

The `notify/` Node.js service is deployed/operated separately and is not part of this chart
(no changes were made to `notify/` — the assignment brief covers Task 4 for the API only).

## Prerequisites

- Kubernetes 1.24+
- [External Secrets Operator](https://external-secrets.io) installed in the cluster, with a
  `SecretStore` (or `ClusterSecretStore`) already configured against your secrets backend
  (e.g. HashiCorp Vault, AWS Secrets Manager). This chart never accepts `SECRET_KEY` or
  `ADMIN_API_KEY` as plain values — it only declares an `ExternalSecret` that pulls them in.
- A CNI that enforces `NetworkPolicy` (e.g. Calico, Cilium) if you want the ingress/egress
  restrictions in this chart to actually take effect.

## Install

```bash
helm upgrade --install vulntracker ./helm/vulntracker \
  --set externalSecret.secretStoreRef.name=<your-secret-store>
```

## Security controls implemented

- **Secrets**: sourced via `ExternalSecret` → backing secrets manager, never hardcoded in
  values.yaml or committed manifests (`templates/externalsecret.yaml`).
- **Network ingress**: default-deny `NetworkPolicy` per namespace; the API only accepts
  ingress from pods matching `networkPolicy.allowedIngressPodLabels` (your ingress
  controller) (`templates/networkpolicy.yaml`).
- **Resource limits**: CPU/memory requests and limits set for the API container
  (`values.yaml` → `api.resources`).
- **Security context**: containers run as non-root, `allowPrivilegeEscalation: false`,
  `readOnlyRootFilesystem: true`, all Linux capabilities dropped, `seccompProfile: RuntimeDefault`
  (`values.yaml` → `securityContext` / `podSecurityContext`).
- **Service account**: dedicated ServiceAccount per release with `automountServiceAccountToken: false`
  (no pod needs the Kubernetes API).

## Values of note

| Key | Description |
|---|---|
| `api.image.repository` / `api.image.tag` | Image pushed to Docker Hub as part of Task 4 |
| `api.config.databaseUrl` | Defaults to a SQLite file on an `emptyDir` volume; swap for a managed DB in production |
| `networkPolicy.allowedIngressPodLabels` | Label selector for whatever sits in front of the API (ingress controller, gateway) |
| `externalSecret.secretStoreRef.name` | Name of the pre-existing `SecretStore`/`ClusterSecretStore` in your cluster |
