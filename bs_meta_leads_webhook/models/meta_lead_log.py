# -*- coding: utf-8 -*-
from odoo import fields, models


class MetaLeadLog(models.Model):
    _name = 'meta.lead.log'
    _description = 'Meta Lead Integration Audit Log'
    _order = 'create_date desc'
    _log_access = False

    name = fields.Char(string='Event', required=True)
    level = fields.Selection(
        [('info', 'Info'), ('warning', 'Warning'), ('error', 'Error')],
        default='info',
        required=True,
    )
    message = fields.Text(string='Message')
    meta_lead_id = fields.Char(string='Meta Lead ID')
    queue_id = fields.Many2one('meta.lead.queue', string='Queue Item', ondelete='set null')
    crm_lead_id = fields.Many2one('crm.lead', string='CRM Lead', ondelete='set null')
    payload = fields.Text(string='Payload Snapshot')
    create_date = fields.Datetime(string='Logged At', readonly=True)
