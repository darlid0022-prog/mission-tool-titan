# Streamlit Community Cloud deployment

This repository is prepared for a free Streamlit Community Cloud deployment. The production dependency source is `environment.yml`; do not add a competing `requirements.txt`, `Pipfile`, or lock file at the repository root because Community Cloud selects only the first supported dependency file in its precedence order.

## Deployment settings

- Repository: `darlid0022-prog/mission-tool-titan`
- Branch: `main`
- Entry point: `app.py`
- Python: **3.13**, selected in **Advanced settings**
- Dependency manager: Conda through `environment.yml`
- Secrets: none required by the current application

PyKEP 3.0.0 is the reason for using Conda: the application imports it directly and conda-forge publishes a Python 3.13 Linux build. The environment contains production runtime packages only. Development tools remain in `requirements-dev.txt` and are not installed by Community Cloud. A Docker or Render fallback is not currently justified.

In Community Cloud, create the app with the settings above and leave the app URL to the platform. Do not configure a fixed port or address. The checked-in `.streamlit/config.toml` enables headless mode, CORS and XSRF protection. Local telemetry is disabled; Community Cloud currently overrides telemetry and some security configuration on hosted apps.

## Pre-deployment verification

From a clean checkout, reproduce the hosted environment:

```bash
conda env create --prefix /tmp/mission-tool-cloud-check --file environment.yml
conda run --prefix /tmp/mission-tool-cloud-check python scripts/verify_streamlit_deployment.py
./check.sh
```

The verification script checks production imports, starts and stops the real `app.py`, probes Streamlit health and the main page, runs the reference launch-window search, builds both correctly separated 3D scenes, generates standalone HTML and PDF exports, and checks public and localhost share-link construction. It writes no mission data to the repository. Use `--detailed` for the refined search and `--skip-server` when a separate server is already under test.

Reference search:

- launch range: 2028-01-01 through 2032-01-01;
- flight time: 1,600 through 3,200 days;
- objective: minimum total delta-v;
- fast grid: 60-day departure and flight-time steps, no refinement;
- retained candidates: 5;
- expected best launch: 2028-06-29;
- expected connected delta-v: approximately 12,554.540 m/s (absolute verification tolerance 0.1 m/s).

The 3D export intentionally produces two scenes. Lambert arcs are heliocentric in AU; Saturn capture arcs are Saturn-centred in km. They must never be placed on the same axes.

## Operational checks after deployment

1. Open the root URL and every navigation page.
2. Run the reference fast search above and confirm five candidates and the expected best result.
3. Select the best candidate and open both 3D reference-frame views.
4. Export the mission PDF and standalone 3D HTML, then open both downloads.
5. Generate a mission share link. A hosted link must retain the deployed origin. A localhost link is shareable only on the same machine until the application is deployed.
6. Run a detailed search only after the fast path succeeds; it performs extra Lambert evaluations and is intended to take longer.
7. Inspect Community Cloud logs for import errors, memory exhaustion, repeated reruns, or cache write failures.

The application uses Streamlit caches, including reconstructible disk caches. Community Cloud storage is ephemeral, so cached values must be treated only as performance aids. PDF and HTML exports are generated in memory. No persistent user data or secrets are written by the application.

## Resource and security notes

The repository has no tracked generated PDF, HTML, image, spreadsheet, environment file, or secrets file. `.gitignore` excludes local environments, secrets, caches, logs, coverage output, and Python bytecode. Before deployment, review the staged diff, run `./check.sh`, and run the secret scan included in `./quality.sh`.

The self-contained Plotly HTML exports embed Plotly JavaScript and are therefore several megabytes each. This affects download size but avoids a CDN dependency. The deployment verifier reports runtime, peak process memory, HTML sizes, PDF size, evaluated Lambert pairs, and ephemeris evaluations. Community Cloud resource limits are not contractual; if a detailed search exceeds them, reduce the user-requested grid density rather than changing scientific formulas.

The share-link implementation derives its origin from the current application URL. No production hostname is hard-coded. If a future deployment reveals a URL or reverse-proxy issue, record it as an application correction rather than inserting a deployment-specific localhost replacement.

## Rollback and deletion

- Roll back application code by selecting the previous known-good commit/tag in Git and redeploying `main`. The requested `v0.2.1` rollback tag is not present in the audited repository; create it only through the normal release process after validation. Until then, record the deployed commit SHA and use that SHA or the existing `v0.2.0` tag as an explicit rollback target.
- Reboot an unhealthy app from its Community Cloud workspace after reviewing logs.
- Delete the hosted app from Community Cloud's app settings if it must be removed. This does not delete the Git repository.
- No account connection, deployment, push, merge, or remote mutation is performed by the repository verification process.

## Sources

- [Streamlit dependency management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
- [Streamlit file organization and working directory](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization)
- [Streamlit deployment and Python selection](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Streamlit Community Cloud platform details](https://docs.streamlit.io/deploy/streamlit-community-cloud/status)
- [Streamlit app management and resource guidance](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app)
- [PyKEP 3.0.0 conda-forge files](https://anaconda.org/channels/conda-forge/packages/pykep/files)
