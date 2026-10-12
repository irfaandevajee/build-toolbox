# Build Toolbox

Generic, owner-triggered Android and Windows build orchestration.

This repository contains only a generic workflow and transfer client. Application source, datasets, API credentials, signing material, build logs, screenshots and release binaries are not tracked here and are not uploaded as public GitHub artifacts or releases.

The owner configures an HTTPS `BUILD_BROKER_URL` repository variable. The broker must validate GitHub OIDC issuer, audience, repository, owner actor, branch, exact workflow commit and a short release authorization expiry. Forks and pull requests do not run builds or obtain private inputs. Signing credentials are obtained only by the authorized release job and are destroyed afterward.

Private inputs and diagnostics remain in the owner's existing private storage. Successful releases are validated and staged there, then published only with the owner's release authorization.

Only standard GitHub-hosted runners are used; caches and GitHub artifact uploads are disabled. This workflow has no schedule. It runs on an owner push or explicit dispatch.
