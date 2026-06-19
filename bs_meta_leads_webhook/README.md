# Meta Leads Webhook Integration for Odoo 19

**Version:** 19.0.1.0.0 | **License:** LGPL-3

Real-time Facebook & Instagram Lead Ads → Odoo CRM integration via Meta Webhooks.

---

## Overview

When a prospect submits a **Lead Ad form** on Facebook or Instagram, this module instantly:

1. Receives the signed webhook from Meta
2. Verifies the HMAC-SHA256 signature
3. Fetches full lead data from the Meta Graph API
4. Creates a `crm.lead` record with all field data, contacts, and UTM attribution

**No polling. No manual imports. No missed leads.**

---

## Key Features

- ⚡ **Real-time** — sub-second webhook delivery from Meta to Odoo CRM
- 🔒 **HMAC-SHA256 verification** — only genuine Meta events accepted
- 🚫 **Zero duplicates** — database-enforced idempotency per `leadgen_id`
- 📋 **Multi-page & multi-form** — per-configuration routing to sales teams
- 🗂 **Custom field mapping** — JSON-based, per lead form
- 👤 **Auto contact creation** — matches existing partners by email/phone
- 📊 **UTM attribution** — campaign, medium, source per configuration
- 🔄 **Auto-retry queue** — failed events reprocessed automatically
- 📝 **Full audit trail** — every event logged with status and error details

---

## Installation

1. Copy `bs_meta_leads_webhook/` into your Odoo addons path:
   ```bash
   cp -r bs_meta_leads_webhook /path/to/odoo/addons/
   ```
   
2. Restart the Odoo service:
   ```bash
   systemctl restart odoo
   ```

3. Update the module list in Odoo:
   - Go to **Settings → Apps → Update Apps List**
   - Or use the CLI: `odoo-bin -d <database> -u bs_meta_leads_webhook --stop-after-init`

4. Install the module:
   - Go to **Settings → Apps**, search for `Meta Leads Webhook Integration`, click **Install**

---

## Quick Setup

### 1. System Parameters

Go to **Settings → Technical → System Parameters** and create:

| Key | Value |
|---|---|
| `meta_leads.app_id` | Your Meta App ID |
| `meta_leads.app_secret` | Your Meta App Secret |
| `meta_leads.verify_token` | A secret string of your choice |

### 2. Meta Webhook

In your [Meta App Dashboard](https://developers.facebook.com/apps) → **Webhooks**:
- Callback URL: `https://yoursite.com/meta/leads/webhook`
- Verify Token: same value as `meta_leads.verify_token`
- Subscribe to field: **`leadgen`**

### 3. Lead Configuration

Go to **Meta Leads → Configurations → New**:
- **Facebook Page ID** — your page's numeric ID
- **Page Access Token** — long-lived token with `leads_retrieval` permission
- **Lead Form ID** — optional; leave blank to catch all forms from the page
- **Sales Team / Salesperson / Stage** — CRM defaults for all leads
- **UTM fields** — for revenue attribution

### 4. Test

Use [Meta Lead Ads Testing Tool](https://developers.facebook.com/tools/lead-ads-testing)
to send a test lead. Within seconds it should appear in **CRM → Leads**.

---

## Default Field Mapping

| Meta Field | Odoo Field |
|---|---|
| `full_name` | Contact Name |
| `email` / `work_email` | Email |
| `phone_number` | Phone |
| `mobile_number` | Mobile |
| `company_name` | Company |
| `job_title` | Job Title |
| `city` / `zip_code` | City / ZIP |
| `country` / `state` | Country / State |
| `website_url` | Website |

Custom questions not in the map are appended to the lead Description.

**Custom mapping example** (JSON tab in Configuration):
```json
{
  "budget_range": "description",
  "CUSTOM_Q_product_interest": "name"
}
```

---

## Webhook Endpoints

| Method | URL | Description |
|---|---|---|
| `GET` | `/meta/leads/webhook` | Meta verification challenge |
| `POST` | `/meta/leads/webhook` | Receive lead events |
| `GET` | `/meta/oauth/start` | Start OAuth token flow |
| `GET` | `/meta/oauth/callback` | OAuth callback handler |

---

## Monitoring

- **Meta Leads → Queue** — all events with state: `pending / done / error`
- **Meta Leads → Audit Log** — immutable history of every processing attempt
- **Scheduled Actions** → *Meta Leads: Process Webhook Queue* — runs every 2 min

---

## Technical Details

- **Odoo versions:** 19.0 (Community & Enterprise)
- **Dependencies:** `base`, `crm`, `mail`, `web`
- **External API:** Meta Graph API v21.0
- **Signature:** HMAC-SHA256 on raw request body
- **Queue model:** `meta.lead.queue` with UNIQUE constraint on `meta_lead_id`
- **Config model:** `meta.lead.config` with `fields.Json` field mapping (PostgreSQL `jsonb`)

---

## Support & Contributing

For issues, questions, or contributions, refer to the project's issue tracking and contribution guidelines in the main repository documentation.

**Module maintained by:** Brain Station 23

