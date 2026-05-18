# -*- coding: utf-8 -*-
{
    "name": "Meta Leads Webhook Integration",
    "version": "19.0.1.0.0",
    "category": "Sales/CRM",
    "summary": "Real-time Facebook & Instagram Lead Ads → Odoo CRM via Meta Webhooks",
    "description": """
Meta Leads Webhook Integration for Odoo 19
===========================================

Automatically capture every Facebook and Instagram Lead Ad submission
into your Odoo CRM in real time — no polling, no manual imports.

Key Features
~~~~~~~~~~~~
* Real-time webhook delivery (sub-second from Meta to Odoo)
* HMAC-SHA256 signature verification — only genuine Meta events accepted
* Idempotent processing — zero duplicate leads, guaranteed
* Multi-page & multi-form support with per-configuration routing
* Configurable JSON field mapping per lead form
* Automatic CRM contact & company matching / creation
* Sales team, salesperson and pipeline stage assignment per form
* UTM campaign / medium / source attribution
* Full audit trail with per-event status log
* Retry queue — failed events auto-reprocess every 2 minutes
* OAuth helper routes for easy Page Access Token management

For detailed setup and configuration, see README.md.
    """,
    "author": "Brain Station 23",
    "license": "LGPL-3",
    "depends": [
        "base",
        "crm",
        "mail",
        "web",
    ],
    "data": [
        "security/meta_leads_security.xml",
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/meta_lead_config_views.xml",
        "views/meta_lead_queue_views.xml",
        "views/meta_lead_log_views.xml",
        "views/crm_lead_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
