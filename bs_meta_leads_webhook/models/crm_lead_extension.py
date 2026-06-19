# -*- coding: utf-8 -*-
from odoo import fields, models


class CrmLeadMetaExtension(models.Model):
    _inherit = 'crm.lead'

    meta_lead_id = fields.Char(
        string='Meta Lead ID',
        index=True,
        copy=False,
        help='Unique lead identifier from Meta Lead Ads',
    )
    meta_form_id = fields.Char(string='Meta Form ID', copy=False)
    meta_page_id = fields.Char(string='Meta Page ID', copy=False)
    meta_ad_id = fields.Char(string='Meta Ad ID', copy=False)
    meta_adset_id = fields.Char(string='Meta Ad Set ID', copy=False)
    meta_campaign_id_raw = fields.Char(string='Meta Campaign ID (raw)', copy=False)
    meta_config_id = fields.Many2one(
        'meta.lead.config',
        string='Meta Lead Config',
        ondelete='set null',
        copy=False,
    )
    meta_created_time = fields.Datetime(string='Meta Lead Created Time', copy=False)
