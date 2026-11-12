# Security policy

This policy covers the images published on <https://images.openimages.cloud>, the build
pipeline in the [open-img-cloud](https://github.com/open-img-cloud) organization, the website
and `oic-sync`.

## Reporting a vulnerability

Do **not** describe a vulnerability in a public issue.

Report it privately through GitHub: open the **Security** tab of the affected repository and
choose **Report a vulnerability** (private vulnerability reporting is enabled on every
repository of the organization). For the build pipeline, use
[`open-img-cloud/.github`](https://github.com/open-img-cloud/.github/security/advisories/new);
for the image distribution service, [`open-img-cloud/images-router`](https://github.com/open-img-cloud/images-router/security/advisories/new);
for a specific image, its own repository. When unsure, use `open-img-cloud/.github`.

The report stays visible only to you and the maintainers until a fix is published.

Vulnerabilities in the software inside an image (kernel, OpenSSL, cloud-init...) belong to the
upstream distribution: report them there. The project republishes fixed images when the
distribution releases them; the daily upstream watchers pick up new releases.

## Supported versions

Only the latest published version of each catalog image is maintained; the version is listed on
its page on <https://openimages.cloud/images/> and in
[`index.json`](https://images.openimages.cloud/index.json). Images with status `archive` follow
an upstream that is end of life or in extended support, as noted on their page.

## Verifying what you run

Every image is signed with cosign keyless signatures bound to the open-img-cloud build
workflows: see [Verifying images](https://github.com/open-img-cloud/docs/blob/main/docs/verifying-images.md).
