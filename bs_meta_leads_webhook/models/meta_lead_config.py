# -*- coding: utf-8 -*-
import json
import logging
import urllib.parse

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class MetaLeadConfig(models.Model):
    _name = "meta.lead.config"
    _description = "Meta Lead Ads Configuration"
    _rec_name = "name"
    _inherit = ["mail.thread"]

    name = fields.Char(string="Configuration Name", required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)

    # Meta identifiers
    page_id = fields.Char(
        string="Facebook Page ID",
        required=True,
        help="The numeric ID of your Facebook Page (e.g. 123456789)",
    )
    form_id = fields.Char(
        string="Lead Form ID",
        help="Optional: restrict to a specific Lead Form ID. Leave empty to process all forms from this page.",
    )
    page_access_token = fields.Char(
        string="Page Access Token",
        required=True,
        help="Long-lived Page Access Token from Meta Graph API.",
    )

    # CRM defaults
    team_id = fields.Many2one("crm.team", string="Sales Team")
    user_id = fields.Many2one("res.users", string="Default Salesperson")
    stage_id = fields.Many2one("crm.stage", string="Initial Stage")
    tag_ids = fields.Many2many("crm.tag", string="Tags")
    lead_type = fields.Selection(
        [("lead", "Lead"), ("opportunity", "Opportunity")],
        string="Lead Type",
        default="lead",
        required=True,
    )

    # UTM
    campaign_id = fields.Many2one("utm.campaign", string="UTM Campaign")
    medium_id = fields.Many2one("utm.medium", string="UTM Medium")
    source_id = fields.Many2one("utm.source", string="UTM Source")

    # Field mapping stored as JSON text — edited via ace widget, parsed at runtime
    field_mapping = fields.Text(
        string="Field Mapping (JSON)",
        default="{}",
        help=(
            "JSON object mapping Meta field names to Odoo crm.lead field names.\n"
            'Example: {"full_name": "contact_name", "email": "email_from", '
            '"phone_number": "phone", "CUSTOM_Q_1": "description"}'
        ),
    )

    lead_count = fields.Integer(
        string="Leads Received", compute="_compute_lead_count", store=False
    )
    last_lead_received = fields.Datetime(string="Last Lead Received")

    def action_view_leads(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Meta Leads",
            "res_model": "crm.lead",
            "view_mode": "list,form",
            "domain": [("meta_config_id", "=", self.id)],
            "context": {"default_meta_config_id": self.id},
        }

    @api.depends()
    def _compute_lead_count(self):
        for record in self:
            record.lead_count = self.env["crm.lead"].search_count(
                [
                    ("meta_config_id", "=", record.id),
                ]
            )

    @api.constrains("field_mapping")
    def _check_field_mapping_is_dict(self):
        for record in self:
            if not record.field_mapping:
                continue
            try:
                parsed = json.loads(record.field_mapping)
            except (ValueError, TypeError):
                raise ValidationError(_("Field Mapping must be valid JSON."))
            if not isinstance(parsed, dict):
                raise ValidationError(
                    _(
                        "Field Mapping must be a JSON object (dict), not a list or scalar."
                    )
                )

    def get_field_mapping(self):
        """Return the field mapping as a Python dict, parsed from the JSON text field."""
        if not self.field_mapping:
            return {}
        try:
            result = json.loads(self.field_mapping)
            return result if isinstance(result, dict) else {}
        except (ValueError, TypeError):
            _logger.warning(
                "MetaLeadConfig id=%s: invalid JSON in field_mapping, ignoring.",
                self.id,
            )
            return {}

    def action_oauth_start(self):
        """Open Meta OAuth dialog directly — builds the full Facebook URL to avoid
        the double-redirect problem where Odoo's act_url handler strips the host."""
        ICP = self.env["ir.config_parameter"].sudo()
        app_id = ICP.get_param("meta_leads.app_id", "")
        base_url = ICP.get_param("web.base.url", "").rstrip("/")
        redirect_uri = base_url + "/meta/oauth/callback"
        params = urllib.parse.urlencode(
            {
                "client_id": app_id,
                "redirect_uri": redirect_uri,
                "scope": "pages_manage_ads,pages_manage_metadata,leads_retrieval,pages_show_list",
                "response_type": "code",
                "state": "odoo_meta_leads",
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": f"https://www.facebook.com/dialog/oauth?{params}",
            "target": "new",
        }
