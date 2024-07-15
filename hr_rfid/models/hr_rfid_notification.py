from markupsafe import Markup

from odoo import fields, models, api, _, SUPERUSER_ID
from odoo.addons.hr_rfid.models.hr_rfid_event_user import action_selection as user_action_selection, HrRfidUserEvent
from odoo.addons.hr_rfid.models.hr_rfid_event_system import action_selection as system_action_selection, HrRfidSystemEvent


class RFIDNotification(models.Model):
    _name = 'hr.rfid.notification'
    _description = 'RFID Notification'
    _sql_constraints = [
        ('no_notification_event',
         'CHECK (user_event IS NOT NULL or system_event IS NOT NULL)',
         'Notification must have at least one checked event!'),
        ('no_notification_recipients',
         'CHECK (notify_followers=True or notify_user_ids IS NOT NULL)',
         'Notification must have at least one recipient!'),
    ]
    name = fields.Char(
        required=True,
    )
    zone_id = fields.Many2one(
        comodel_name='hr.rfid.zone',
        string='Zone',
        required=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        related='zone_id.company_id',
    )
    notification_type = fields.Selection(
        [
            ('discuss', _('System Chat')),
            ('email', _('Email')),
            # ('sms', _('SMS Message')),
        ], default='discuss',
    )
    user_event = fields.Selection(
        selection=user_action_selection,
        string='User Event',
    )
    system_event = fields.Selection(
        selection=system_action_selection[19:],
        string='System Event',
    )
    notify_followers = fields.Boolean(
        string='Notify Followers',
        default=True,
    )
    notify_partner_ids = fields.Many2many(
        comodel_name='res.partner',
        help='''Partners to notify:
                * Only Partners with a user account can receive "System Chat" notifications.
                * Only Partners with an email address can receive "Email" notifications.
                * Only Partners with a mobile phone number can receive "SMS Message" notifications.''',
        default=lambda self: self.env.context.get('default_contact_id', None),
        check_company=True,
        domain=[('is_company', '=', False)],
    )

    def _make_message(self, event):
        notify_title = event.get_event_action_text()
        # notify_title = getattr(event, 'error_description', None) or getattr(event, 'display_name', None)
        is_system_event = isinstance(event, HrRfidSystemEvent)
        event_link = event._notify_get_action_link('view')
        door_link = event.door_id and event.door_id._notify_get_action_link('view') or None
        partner_link = None
        if not is_system_event:
            partner_link = event.contact_id and event.contact_id._notify_get_action_link(
                'view') or event.employee_id and event.employee_id._notify_get_action_link('view') or None
            partner_name = event.contact_id and event.contact_id.name or event.employee_id and event.employee_id.name or None
        # generate html code for door link
        door_link = door_link and Markup('<a href="%s">%s</a>') % (door_link, event.door_id.name) or None
        # generate html code for partner link
        partner_link = partner_link and Markup('<a href="%s">%s</a>') % (partner_link, partner_name) or None
        # generate html code for event link
        event_link = event_link and Markup('<a href="%s">%s</a>') % (event_link, event.name) or event.name
        notify_message = Markup("<h5>%s</h5><p>%s</p><p>%s</p>") % (
            _('RFID Notification for %s', event_link),
            _('Where: %s', door_link),
            _('When: %s', getattr(event, 'timestamp', None) or getattr(event, 'event_time', None)),
        )
        notify_message += Markup("<p>%s</p>") % (
            _('Who: %s', partner_link)
        ) if partner_link else ''
        return notify_title, notify_message

    def process_event(self, event):
        for notification in self:
            if notification.user_event == event.event_action or notification.system_event == event.event_action:
                recipients = notification.notify_partner_ids
                recipients += notification.zone_id.message_follower_ids.partner_id if notification.notify_followers else self.env['res.partner']
                for recipient in recipients:
                    notify_title, notify_message = self.with_context(lang=recipient.lang)._make_message(
                        event)
                    if notification.notification_type == 'discuss' and recipient.user_ids:
                        notification._notify_by_discuss([recipient], notify_message)
                    elif notification.notification_type == 'email':
                        notification._notify_by_email([recipient], notify_title, notify_message)
                    elif notification.notification_type == 'sms':
                        pass

    def _notify_by_discuss(self, recipients, msg):
        odoobot_id = self.env.ref("base.partner_root").id
        for recipient in recipients:
            partners_to = [recipient.id]
            channel = self.env["discuss.channel"].with_user(SUPERUSER_ID).channel_get(partners_to)
            channel.message_post(body=msg, author_id=odoobot_id, message_type="comment",
                                 subtype_xmlid="mail.mt_comment")

    def _notify_by_email(self, recipients, subject, body):
        for recipient in recipients:
            if recipient.email:
                odoobot = self.env.ref('base.partner_root')
                # mail_template = self.station_id.mail_template_id
                # ctx = {'recipient_name': recipient.name, 'lang': recipient.user_partner_id.lang}
                # body = mail_template.with_context(ctx)._render_field('body_html', self.ids, compute_lang=True)[self.id]
                # subject = mail_template.with_context(ctx)._render_field('subject', self.ids, compute_lang=True)[self.id]
                recipient.message_notify(
                    email_from=odoobot.email_formatted,
                    author_id=self.env.user.partner_id.id,
                    body=body,
                    subject=subject,
                    partner_ids=recipient.ids,
                    email_layout_xmlid='mail.mail_notification_light',
                    force_send=True,
                )

    def _notify_by_sms(self, recipients, msg):
        for host in self.host_ids:
            if host.work_phone:
                odoobot_id = self.env['ir.model.data']._xmlid_to_res_id("base.partner_root")
                sms_template = self.station_id.sms_template_id
                body = sms_template._render_field('body', self.ids, compute_lang=True)[self.id]
                host._message_sms(
                    author_id=odoobot_id,
                    body=body,
                    partner_ids=host.user_partner_id.ids,
                )
