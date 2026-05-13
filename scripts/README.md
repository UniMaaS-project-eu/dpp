````md
# Automation Scripts (DPP)

This folder contains the project’s operational scripts to avoid repetitive manual steps.

## Quick Summary

| Script | What it does | When to use it |
|---|---|---|
| `scripts/deploy.sh` | Starts the full Docker stack interactively, detects port conflicts, validates Keycloak, and checks endpoints | When starting the project locally, especially if you have other stacks running |
| `scripts/init-keycloak.sh` | Initializes Keycloak for the app: creates/updates the realm and OIDC client, optionally creates a demo user, and updates `.env` | After starting the services, to make authentication ready without configuring Keycloak manually |
| `deploy.sh` (root) | Compatibility wrapper that delegates to `scripts/deploy.sh` | If you were already used to running `./deploy.sh` |

---

## 1) `scripts/deploy.sh`

### Objective

Automate the complete local deployment of the DPP stack and reduce common startup issues.

### What it validates / configures

- Checks dependencies (`docker`, `docker compose`, `ss`, `curl`).
- Reads `.env` and optionally asks whether you want to review the configuration before startup.
- Detects ports used by other projects and suggests free ports.
- Checks whether the configured Keycloak version is compatible with the machine.
- Starts containers with `docker compose up -d --build`.
- Checks the availability of `web`, `orion`, and `keycloak`.
- If it detects `Local access required` in Keycloak, it offers automatic repair by resetting only Keycloak data.

### Usage

```bash
./scripts/deploy.sh
````

### Important Notes

* The “Keycloak repair” flow may delete the Keycloak data volume for that service only, so any previous realm/client configuration in that container would be lost.
* The script is intended for **local development**.

---

## 2) `scripts/init-keycloak.sh`

### Objective

Prepare Keycloak so that web login/registration works as described in the README, without manual configuration in the Keycloak console.

### What it does exactly

* Ensures that the `keycloak` service is running.
* Prompts for interactive input:

  * target realm
  * client ID
  * extra hosts for redirect URIs
* Authenticates against the Keycloak Admin API using:

  * `KEYCLOAK_ADMIN`
  * `KEYCLOAK_ADMIN_PASSWORD`
* Creates the realm if it does not exist (default: `unimaas`) or applies recommended settings if it already exists.
* Creates/updates the app OIDC client:

  * confidential client
  * standard flow
  * redirect URIs
  * post logout redirect URIs
* Retrieves/reuses the client `client_secret`.
* Updates `.env` with:

  * `KEYCLOAK_REALM`
  * `KEYCLOAK_CLIENT_ID`
  * `KEYCLOAK_CLIENT_SECRET`
* Optionally creates/updates a demo user in the realm.
* Optionally recreates the `web` service to immediately apply the `.env` changes.

### Usage

```bash
./scripts/init-keycloak.sh
```

### When to run it

* The first time you start the project.
* When you change the Keycloak realm or client.
* If you regenerated the client secret and want to synchronize `.env`.

---

## Recommended Workflow

1. Start the stack:

   ```bash
   ./scripts/deploy.sh
   ```

2. Initialize Keycloak:

   ```bash
   ./scripts/init-keycloak.sh
   ```

3. Access the DPP web application and test login/registration.

---

## Maintenance

* Both scripts are documented by blocks and functions to make maintenance easier.
* If you add new environment variables related to ports or Keycloak, update these scripts and this README.

```
```

