# BrainStation-23 · Dessert Rice

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Odoo](https://img.shields.io/badge/Odoo-19.0-714B67.svg)](https://www.odoo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

Custom Odoo development repository maintained by **BrainStation-23** for production-grade addons, extensions, and implementation assets.

## Overview

This repository is intended for Odoo custom development projects targeting **Odoo 19.0**. It is suitable for business-specific modules, technical customizations, reporting, integrations, and deployment-ready improvements built using Odoo and OCA best practices.

## Supported Stack

- **Odoo:** 19.0
- **Python:** 3.10+
- **PostgreSQL:** 14+
- **Deployment targets:** local, staging, on-prem, Docker, Odoo.sh

## Recommended Repository Structure

```text
dessert-rice/
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── CHANGELOG.md
├── requirements.txt
├── setup/
├── erp/
│   └── custom_addons/
├── erp-accounting/
└── oca-addons/
```

> For BrainStation-23 ERP environments, common addon roots may include `erp/custom_addons`, `erp-accounting`, and `oca-addons`.

## Installation

1. Clone the repository:
   ```bash
   git clone git@github.com:BrainStation-23/dessert-rice.git
   cd dessert-rice
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install Python dependencies:
   ```bash
   pip install -U pip wheel
   pip install -r requirements.txt
   ```
4. Add the custom addons paths to your `odoo.conf`:
   ```ini
   addons_path = /opt/odoo/odoo/addons,/opt/odoo/dessert-rice/erp/custom_addons,/opt/odoo/dessert-rice/erp-accounting,/opt/odoo/dessert-rice/oca-addons
   ```
5. Restart Odoo and update the apps list in developer mode.

## Development Setup

- Use isolated branches for all changes.
- Follow Odoo manifest conventions and keep dependencies explicit.
- Run tests for impacted modules before opening a pull request.
- Validate upgrades with `-u <module_name>` on a staging database before production deployment.

Example local update command:

```bash
./odoo-bin -c /etc/odoo/odoo.conf -d <database> -u <module_name> --stop-after-init
```

## Module Guidelines

- One business concern per module where practical
- Clean manifests and dependency declarations
- Migration-safe XML IDs and data files
- Access rules and security reviewed for every model change
- Tests added for critical business flows

## Contributing

Please read [CONTRIBUTING.md](./CONTRIBUTING.md) before creating branches, commits, or pull requests.

## License

This project is licensed under the [MIT License](./LICENSE).
