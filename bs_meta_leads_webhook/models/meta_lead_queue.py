# -*- coding: utf-8 -*-
import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class MetaLeadQueue(models.Model):
    _name = "meta.lead.queue"
    _description = "Meta Lead Webhook Queue"
    _order = "create_date desc"

    meta_lead_id = fields.Char(
        string="Meta Lead ID",
        required=True,
        index=True,
        help="Unique Lead ID from Meta (leadgen_id)",
    )
    page_id = fields.Char(string="Page ID", index=True)
    form_id = fields.Char(string="Form ID")
    ad_id = fields.Char(string="Ad ID")
    adset_id = fields.Char(string="Ad Set ID")
    campaign_id_meta = fields.Char(string="Meta Campaign ID")

    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("done", "Done"),
            ("error", "Error"),
            ("duplicate", "Duplicate"),
        ],
        default="pending",
        required=True,
        index=True,
    )
    raw_payload = fields.Text(string="Raw Webhook Payload")
    lead_data = fields.Text(string="Lead Data (from Graph API)")
    error_message = fields.Text(string="Error Message")
    retry_count = fields.Integer(string="Retry Count", default=0)

    crm_lead_id = fields.Many2one(
        "crm.lead", string="Created CRM Lead", ondelete="set null"
    )
    config_id = fields.Many2one("meta.lead.config", string="Configuration Used")

    received_at = fields.Datetime(string="Received At", default=fields.Datetime.now)
    processed_at = fields.Datetime(string="Processed At")

    _meta_lead_id_unique = models.Constraint(
        "unique(meta_lead_id)",
        "A lead with this Meta Lead ID already exists (idempotency guard).",
    )

    def action_retry(self):
        """Manually retry failed queue items."""
        self.filtered(lambda r: r.state == "error").write(
            {
                "state": "pending",
                "error_message": False,
            }
        )
        self.env["meta.lead.queue"]._process_pending_queue()

    @api.model
    def _process_pending_queue(self):
        """Cron job entry point: process all pending queue items."""
        from ..services.meta_api_service import MetaAPIService
        from ..services.lead_mapper import LeadMapper

        pending = self.search(
            [
                ("state", "=", "pending"),
                ("retry_count", "<", 5),
            ],
            order="create_date asc",
            limit=100,
        )

        _logger.info("Meta Lead Queue: processing %d pending item(s).", len(pending))

        for item in pending:
            item.write({"state": "processing"})
            self.env.cr.commit()
            try:
                config = item.config_id or self._find_config(item.page_id, item.form_id)
                if not config:
                    self.env["meta.lead.log"].create(
                        {
                            "name": "No config found",
                            "level": "warning",
                            "message": f"No active Meta Lead Config for page_id={item.page_id}, form_id={item.form_id}",
                            "meta_lead_id": item.meta_lead_id,
                            "queue_id": item.id,
                        }
                    )
                    raise ValueError(
                        "No active Meta Lead Config found for page_id=%s, form_id=%s"
                        % (item.page_id, item.form_id)
                    )

                api_service = MetaAPIService(self.env)
                lead_data = api_service.fetch_lead(
                    item.meta_lead_id, config.page_access_token
                )
                item.lead_data = json.dumps(lead_data, indent=2)

                mapper = LeadMapper(self.env)
                crm_lead = mapper.create_lead(lead_data, config, item)

                item.write(
                    {
                        "state": "done",
                        "crm_lead_id": crm_lead.id,
                        "processed_at": fields.Datetime.now(),
                        "config_id": config.id,
                    }
                )
                config.last_lead_received = fields.Datetime.now()
                self.env["meta.lead.log"].create(
                    {
                        "name": "Lead processed",
                        "level": "info",
                        "message": f"crm.lead id={crm_lead.id} created for meta_lead_id={item.meta_lead_id}",
                        "meta_lead_id": item.meta_lead_id,
                        "queue_id": item.id,
                        "crm_lead_id": crm_lead.id,
                        "payload": item.raw_payload,
                    }
                )
                _logger.info(
                    "Meta Lead Queue: lead %s → crm.lead id=%s",
                    item.meta_lead_id,
                    crm_lead.id,
                )

            except Exception as exc:
                item.write(
                    {
                        "state": "error",
                        "error_message": str(exc),
                        "retry_count": item.retry_count + 1,
                    }
                )
                self.env["meta.lead.log"].create(
                    {
                        "name": "Lead processing error",
                        "level": "error",
                        "message": str(exc),
                        "meta_lead_id": item.meta_lead_id,
                        "queue_id": item.id,
                        "payload": item.raw_payload,
                    }
                )
                _logger.exception(
                    "Meta Lead Queue: error processing item id=%s meta_lead_id=%s: %s",
                    item.id,
                    item.meta_lead_id,
                    exc,
                )

            self.env.cr.commit()

    @api.model
    def _find_config(self, page_id, form_id):
        """Find the best matching MetaLeadConfig for page_id / form_id."""
        domain_base = [("active", "=", True), ("page_id", "=", page_id)]

        # 1. Exact match: page + form
        if form_id:
            config = self.env["meta.lead.config"].search(
                domain_base + [("form_id", "=", form_id)], limit=1
            )
            if config:
                return config

        # 2. Page-level catch-all (form_id not set on config)
        config = self.env["meta.lead.config"].search(
            domain_base + [("form_id", "in", [False, ""])], limit=1
        )
        if config:
            return config

        # 3. Any active config for this page
        return self.env["meta.lead.config"].search(domain_base, limit=1)
