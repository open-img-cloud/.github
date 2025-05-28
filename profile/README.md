# Open Images

**Open Images** delivers secure, cloud-ready operating system images (Linux, Windows, BSD, etc.) for **OpenStack** and **Proxmox** environments.

---

## 🚀 Our Mission

We aim to automate, standardize, and maintain high-quality OS images through GitHub-based CI pipelines. Our images are reproducible, optimized, and ready for deployment in production-grade cloud infrastructures.

---

## ✅ What We Offer

- 🖥️ Multi-OS support: Linux, Windows, BSD, etc.
- 🔁 Automated CI pipelines (GitHub Actions)
- 🔒 Hardened and security-verified builds
- ☁️ Native compatibility with OpenStack & Proxmox
- 📦 Versioned image releases with transparent changelogs

---

## 📦 Available Images

### Linux Images

| OS                | Status           | Formats             | Repository link                                     |
|-------------------|------------------|---------------------|-----------------------------------------------------|
| Alpaquita Linux   | ✅ Stable        | QCOW2               | https://github.com/open-img-cloud/alpaquita-linux   |
| Alpine Linux      | 🚧 Building      | QCOW2               | https://github.com/open-img-cloud/alpine-linux      |
| Amazon Linux 2    | ✅ Stable        | QCOW2               | https://github.com/open-img-cloud/amazon-linux-2    |
| Amazon Linux 2023 | ✅ Stable        | QCOW2               | https://github.com/open-img-cloud/amazon-linux-2023 |

### Windows Images

| OS                     | Status          | Formats             | Repository link                                          |
|------------------------|-----------------|---------------------|----------------------------------------------------------|
| Windows Server 2025    | 🚧 Building     | QCOW2               | https://github.com/open-img-cloud/windows-server-2025    |
| Windows Server 2022    | 🚧 Building     | QCOW2               | https://github.com/open-img-cloud/windows-server-2022    |
| Windows Server 2019    | 🚧 Building     | QCOW2               | https://github.com/open-img-cloud/windows-server-2019    |
| WIndows Server 2016    | 🚧 Building     | QCOW2               | https://github.com/open-img-cloud/windows-server-2016    |
| Windows Server 2012 R2 | 🚧 Building     | QCOW2               | https://github.com/open-img-cloud/windows-server-2012-r2 |

### BSD Images

| OS                | Status           | Formats             | Repository link                           |
|-------------------|------------------|---------------------|-------------------------------------------|
| FreeBSD           | 🚧 Building      | QCOW2               | https://github.com/open-img-cloud/freebsd |


---

## 🛠️ How It Works

We leverage tools such as:

- **Libguestfs Tools** to build and customize disk images
- **GitHub Actions** for automated CI/CD workflows
- **cloud-init** for provisioning compatibility
- **Validation pipelines** to ensure image quality

---

## 📜 Licensing

This project’s infrastructure and tooling are open-sourced under the [MIT License](LICENSE), unless otherwise stated.

⚠️ **Note:**  
The **operating system images** produced by this project **inherit the licensing terms of their respective upstream OS distributions** (e.g., Ubuntu, Debian, Windows, etc.).  
Please review the original licenses of each OS before using them in your infrastructure.

---

## 🤝 Join Us

Whether you're a DevOps engineer, cloud architect, or open-source contributor — you're welcome!  
Check out our repositories, open issues, or suggest new OS support.

> 💬 **Got a request?** Open an issue or start a discussion in our repo.

---

**Build once. Deploy anywhere.**
