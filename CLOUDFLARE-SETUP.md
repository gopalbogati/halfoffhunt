# Cloudflare Pages setup

Status: deployment support is prepared. No Cloudflare project or free address has been created by this change.

Cloudflare Pages supplies a free `<project-name>.pages.dev` subdomain. This is not a free `.com` or `.com.au` registration. Availability is checked when creating the project.

## One-time account setup

1. Sign in to Cloudflare, open Workers & Pages, and create a **Pages Direct Upload** project. Try `halfoffhunt` if available. Record the actual project name and `pages.dev` address. Use production branch `main`.
2. Create an API token with **Account → Cloudflare Pages → Edit**, scoped to only the account containing this project. Do not grant DNS, billing or unrelated account permissions.
3. In this GitHub repository, Settings → Secrets and variables → Actions, add repository secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`. Never put the token in chat, source code, or issues.
4. After both secrets and the project exist, add repository **variable** `CLOUDFLARE_PROJECT_NAME` with the actual project name. This switches subsequent workflow deployments to Cloudflare and stops GitHub Pages deployments.
5. Run the existing **deals** workflow manually. Confirm its Cloudflare deployment step succeeds and open the assigned `pages.dev` address. Verify deals load, filters work, and project sharing points to the new address.
6. After verification, turn off the old GitHub Pages site in repository settings and update public profile links. The old published site is not automatically removed by this workflow.

The scanner and its cached deal data still run in GitHub Actions. Only the generated `site/` directory is uploaded to Cloudflare; private alert state and credentials are not uploaded. Scheduled execution is best effort, not guaranteed exact timing. Monitor free-tier limits as usage grows.

The workflow sets the canonical URL, sitemap and LinkedIn sharing URL from the configured project name. To move to a purchased custom domain later, update this configuration deliberately after DNS verification.

Do not enable plain GitHub-connected builds with only `python3 build_site.py`: the scanned deals are in the Actions cache, not committed to the repository. This project uses Direct Upload after the scanner runs.

Official guide: https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/
