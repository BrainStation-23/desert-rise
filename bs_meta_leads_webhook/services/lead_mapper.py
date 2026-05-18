# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from typing import Optional

from odoo import fields

_logger = logging.getLogger(__name__)

# Default mapping: Meta field name → Odoo crm.lead field name
DEFAULT_FIELD_MAP = {
    "full_name": "contact_name",
    "first_name": "_meta_first_name",  # combined with last_name
    "last_name": "_meta_last_name",  # combined with first_name
    "email": "email_from",
    "work_email": "email_from",
    "phone_number": "phone",
    "mobile_number": "mobile",
    "company_name": "partner_name",
    "job_title": "function",
    "zip_code": "zip",
    "city": "city",
    "state": "state_id",  # resolved by name lookup
    "country": "country_id",  # resolved by name/code lookup
    "street_address": "street",
    "website_url": "website",
}


class LeadMapper:
    """
    Maps Meta Lead Ads field_data to an Odoo crm.lead record.
    Applies DEFAULT_FIELD_MAP merged with the per-config custom JSON mapping.
    """

    def __init__(self, env):
        self.env = env

    def create_lead(self, lead_data: dict, config, queue_item) -> object:
        """
        Create a crm.lead from Meta Graph API lead data and a meta.lead.config record.

        :param lead_data: dict returned by MetaAPIService.fetch_lead()
        :param config:    meta.lead.config recordset
        :param queue_item: meta.lead.queue recordset (for cross-reference only)
        :return: crm.lead recordset
        """
        meta_fields = self._parse_field_data(lead_data.get("field_data", []))

        combined_map = {**DEFAULT_FIELD_MAP, **config.get_field_mapping()}
        crm_vals = {}
        first_name = ""
        last_name = ""
        extra_lines = []

        for meta_key, value in meta_fields.items():
            if not value:
                continue
            odoo_field = combined_map.get(meta_key)
            if not odoo_field:
                extra_lines.append(f"{meta_key}: {value}")
                continue

            if odoo_field == "_meta_first_name":
                first_name = value
            elif odoo_field == "_meta_last_name":
                last_name = value
            elif odoo_field == "state_id":
                resolved = self._resolve_state(value, crm_vals.get("country_id"))
                if resolved:
                    crm_vals["state_id"] = resolved
            elif odoo_field == "country_id":
                resolved = self._resolve_country(value)
                if resolved:
                    crm_vals["country_id"] = resolved
            elif odoo_field == "email_from":
                # First email field wins; work_email does not overwrite a captured email
                crm_vals.setdefault("email_from", value)
            else:
                crm_vals[odoo_field] = value

        # Compose contact_name from first + last when full_name not provided
        if not crm_vals.get("contact_name"):
            full = f"{first_name} {last_name}".strip()
            if full:
                crm_vals["contact_name"] = full

        # Meta metadata fields
        crm_vals.update(
            {
                "meta_lead_id": str(lead_data.get("id", "")),
                "meta_form_id": str(lead_data.get("form_id", "")),
                "meta_page_id": str(config.page_id),
                "meta_ad_id": str(lead_data.get("ad_id", "")),
                "meta_adset_id": str(lead_data.get("adset_id", "")),
                "meta_campaign_id_raw": str(lead_data.get("campaign_id", "")),
                "meta_config_id": config.id,
                "meta_created_time": self._parse_meta_datetime(
                    lead_data.get("created_time")
                ),
            }
        )

        # CRM defaults from configuration
        crm_vals["type"] = config.lead_type if config and config.lead_type else "lead"
        if config.team_id:
            crm_vals["team_id"] = config.team_id.id
        if config.user_id:
            crm_vals["user_id"] = config.user_id.id
        if config.stage_id:
            crm_vals["stage_id"] = config.stage_id.id
        if config.tag_ids:
            crm_vals["tag_ids"] = [(6, 0, config.tag_ids.ids)]
        if config.campaign_id:
            crm_vals["campaign_id"] = config.campaign_id.id
        if config.medium_id:
            crm_vals["medium_id"] = config.medium_id.id
        if config.source_id:
            crm_vals["source_id"] = config.source_id.id

        # Lead name
        contact = (
            crm_vals.get("contact_name") or crm_vals.get("email_from") or "Meta Lead"
        )
        crm_vals.setdefault("name", f"[Meta] {contact} — {config.name}")

        # Description: source info header + any unmapped custom fields
        source_info = (
            f"Source: Meta Lead Ads\n"
            f"Config: {config.name}\n"
            f"Page ID: {config.page_id}\n"
            f"Form ID: {lead_data.get('form_id', '')}\n"
            f"Lead ID: {lead_data.get('id', '')}\n"
            f"Ad ID: {lead_data.get('ad_id', '')}\n"
        )
        if extra_lines:
            source_info += "\nCustom Fields:\n" + "\n".join(extra_lines)

        existing_desc = crm_vals.get("description", "")
        crm_vals["description"] = source_info + (
            "\n\n" + existing_desc if existing_desc else ""
        )

        crm_lead = self.env["crm.lead"].sudo().create(crm_vals)
        _logger.info(
            "LeadMapper: created crm.lead id=%s for meta_lead_id=%s",
            crm_lead.id,
            lead_data.get("id"),
        )
        return crm_lead

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _parse_field_data(field_data: list) -> dict:
        """Convert Meta's field_data array to a flat {name: value} dict."""
        result = {}
        for item in field_data:
            name = item.get("name", "")
            values = item.get("values", [])
            result[name] = values[0] if values else ""
        return result

    def _resolve_country(self, value: str):
        if not value:
            return False
        country = (
            self.env["res.country"]
            .sudo()
            .search(
                [
                    "|",
                    ("name", "ilike", value),
                    ("code", "=ilike", value),
                ],
                limit=1,
            )
        )
        return country.id if country else False

    def _resolve_state(self, value: str, country_id: Optional[int] = None):
        if not value:
            return False
        domain = [("name", "ilike", value)]
        if country_id:
            domain.append(("country_id", "=", country_id))
        state = self.env["res.country.state"].sudo().search(domain, limit=1)
        return state.id if state else False

    @staticmethod
    def _parse_meta_datetime(raw: str):
        """Parse Meta ISO 8601 datetime string (UTC) to Odoo-compatible naive datetime string."""
        if not raw:
            return False
        for fmt in ("%Y-%m-%dT%H:%M:%S+0000", "%Y-%m-%dT%H:%M:%S+00:00"):
            try:
                dt = datetime.strptime(raw, fmt)
                return fields.Datetime.to_string(dt)
            except ValueError:
                continue
        _logger.warning("LeadMapper: could not parse Meta datetime: %s", raw)
        return False
