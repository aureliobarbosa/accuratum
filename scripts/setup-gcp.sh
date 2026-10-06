#!/usr/bin/env bash
# One-time Google Cloud setup for the website's deploy (Step 7d). Adapted
# from Bingo's scripts/configura-gcp.sh.
#
# Run it in Cloud Shell (gcloud is there and logged in), or anywhere with the
# Google Cloud CLI after `gcloud init`:
#
#   git clone https://github.com/aureliobarbosa/accuratum.git
#   cd accuratum && PROJECT=<project-id> bash scripts/setup-gcp.sh
#
# Safe to run again: what already exists is reused, not an error. At the end
# it prints the four values for the repository's GitHub Variables.
set -euo pipefail

PROJECT="${PROJECT:?set PROJECT to the Google Cloud project id}"
REGION="${REGION:-southamerica-east1}" # keep equal to deploy.yml and firebase.json
REPOSITORY="${REPOSITORY:-accuratum}"
GITHUB_REPO="${GITHUB_REPO:-aureliobarbosa/accuratum}"

# gcloud's `create` fails when the resource exists. That one failure counts as
# success so the script can be rerun; any other still aborts (set -e).
create() {
  local what="$1"; shift
  echo "==> ${what}"
  if out=$("$@" 2>&1); then
    printf '%s\n' "${out}"
  elif printf '%s' "${out}" | grep -qi "already exists\|ALREADY_EXISTS"; then
    echo "    already there, moving on"
  else
    printf '%s\n' "${out}" >&2
    return 1
  fi
}

command -v gcloud >/dev/null || {
  echo "gcloud not found. Use Cloud Shell or install the Google Cloud CLI." >&2
  exit 1
}

echo "Project: ${PROJECT} | Region: ${REGION} | GitHub repo: ${GITHUB_REPO}"
gcloud config set project "${PROJECT}" >/dev/null
PROJECT_NUMBER="$(gcloud projects describe "${PROJECT}" --format='value(projectNumber)')"

# sts and iamcredentials are what Workload Identity Federation uses to swap
# GitHub's token for temporary credentials.
echo "==> Enabling the APIs (slow the first time)"
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  --project="${PROJECT}"

create "Artifact Registry repository" \
  gcloud artifacts repositories create "${REPOSITORY}" \
    --project="${PROJECT}" --repository-format=docker --location="${REGION}" \
    --description="Accuratum website images"

# What CI deploys with.
create "Deploy service account" \
  gcloud iam service-accounts create github-deploy \
    --project="${PROJECT}" --display-name="Deploy from GitHub Actions"

# What the container runs as. It has NO roles on purpose: the service is
# stateless and calls nothing in Google. Without it Cloud Run would use the
# default Compute account, which often has Editor on the whole project.
create "Runtime service account" \
  gcloud iam service-accounts create accuratum-runtime \
    --project="${PROJECT}" --display-name="Accuratum website at run time"

SA_DEPLOY="github-deploy@${PROJECT}.iam.gserviceaccount.com"
SA_RUNTIME="accuratum-runtime@${PROJECT}.iam.gserviceaccount.com"

echo "==> Roles of the deploy account"
gcloud projects add-iam-policy-binding "${PROJECT}" \
  --member="serviceAccount:${SA_DEPLOY}" \
  --role="roles/artifactregistry.writer" --condition=None >/dev/null
gcloud projects add-iam-policy-binding "${PROJECT}" \
  --member="serviceAccount:${SA_DEPLOY}" \
  --role="roles/run.admin" --condition=None >/dev/null

# To deploy a service that runs AS accuratum-runtime, the CI account must be
# allowed to act as it. This is what's usually missing on the first try.
gcloud iam service-accounts add-iam-policy-binding "${SA_RUNTIME}" \
  --project="${PROJECT}" --member="serviceAccount:${SA_DEPLOY}" \
  --role="roles/iam.serviceAccountUser" >/dev/null

create "GitHub identity pool" \
  gcloud iam workload-identity-pools create "github" \
    --project="${PROJECT}" --location="global" --display-name="GitHub Actions"

# --attribute-condition is the security piece: without it ANY GitHub
# repository in the world could trade its token for access to this project.
create "OIDC provider pinned to ${GITHUB_REPO}" \
  gcloud iam workload-identity-pools providers create-oidc "accuratum" \
    --project="${PROJECT}" --location="global" \
    --workload-identity-pool="github" --display-name="accuratum repository" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
    --attribute-condition="assertion.repository == '${GITHUB_REPO}'" \
    --issuer-uri="https://token.actions.githubusercontent.com"

echo "==> Letting the repository use the deploy account"
gcloud iam service-accounts add-iam-policy-binding "${SA_DEPLOY}" \
  --project="${PROJECT}" --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/attribute.repository/${GITHUB_REPO}" \
  >/dev/null

# One image per deploy; without a policy the registry grows forever.
echo "==> Artifact Registry cleanup policy"
gcloud artifacts repositories set-cleanup-policies "${REPOSITORY}" \
  --project="${PROJECT}" --location="${REGION}" \
  --policy="$(dirname "$0")/artifact-registry-cleanup.json" >/dev/null

PROVIDER="$(gcloud iam workload-identity-pools providers describe "accuratum" \
  --project="${PROJECT}" --location="global" \
  --workload-identity-pool="github" --format='value(name)')"

cat <<SUMMARY

======================================================================
Done. Now add these four Variables on GitHub, in
  Settings -> Secrets and variables -> Actions -> Variables tab
  -> New repository variable

  GCP_PROJECT_ID     ${PROJECT}
  GCP_WIF_PROVIDER   ${PROVIDER}
  GCP_SA_DEPLOY      ${SA_DEPLOY}
  GCP_SA_RUNTIME     ${SA_RUNTIME}

They are identifiers, not credentials: no key was created. The provider's
condition, pinned to ${GITHUB_REPO}, is what authorizes the deploy.

Then a site-v* tag deploys.
======================================================================
SUMMARY
