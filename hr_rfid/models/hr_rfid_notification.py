from markupsafe import Markup
from pytz import timezone, UTC

from odoo import fields, models, api, _, SUPERUSER_ID
from odoo.addons.hr_rfid.models.hr_rfid_event_user import action_selection as user_action_selection, HrRfidUserEvent
from odoo.addons.hr_rfid.models.hr_rfid_event_system import action_selection as system_action_selection, \
    HrRfidSystemEvent
from odoo.exceptions import UserError


class RFIDNotification(models.Model):
    _name = 'hr.rfid.notification'
    _description = 'RFID Notification'
    _sql_constraints = [
        ('no_notification_event',
         'CHECK (user_event IS NOT NULL or system_event IS NOT NULL)',
         'Notification must have at least one checked event!'),
        ('no_notification_recipients',
         'CHECK (notify_followers or notify_user_ids IS NOT NULL)',
         'Notification must have at least one recipient!'),
    ]

    name = fields.Char(
        compute='_default_name'
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

    def get_notification_type_text(self):
        self.ensure_one()
        selection_dict = dict(self.fields_get(allfields=['notification_type'])['notification_type']['selection'])
        text = selection_dict.get(self.notification_type)
        return text

    def get_user_event_text(self):
        self.ensure_one()
        selection_dict = dict(self.fields_get(allfields=['user_event'])['user_event']['selection'])
        text = selection_dict.get(self.user_event)
        return text

    def get_system_event_text(self):
        self.ensure_one()
        selection_dict = dict(self.fields_get(allfields=['system_event'])['system_event']['selection'])
        text = selection_dict.get(self.system_event)
        return text

    @api.depends('user_event', 'system_event', 'notification_type')
    def _default_name(self):
        for rec in self:
            rec.name = '%s (%s)' % (rec.get_system_event_text() or rec.get_user_event_text(), rec.get_notification_type_text(),)

    def make_message(self, event, partner_id):
        notify_title = event.get_event_action_text()
        # notify_title = getattr(event, 'error_description', None) or getattr(event, 'display_name', None)
        is_system_event = isinstance(event, HrRfidSystemEvent)
        event_link = event._notify_get_action_link('view')
        door_link = event.door_id and event.door_id._notify_get_action_link('view') or None
        controller_link = getattr(event, 'controller_id', None) and event.controller_id and event.controller_id._notify_get_action_link('view') or None
        webstack_link = getattr(event, 'webstack_id', None) and event.webstack_id and event.webstack_id._notify_get_action_link('view') or None
        partner_link = None
        if not is_system_event:
            partner_link = event.contact_id and event.contact_id._notify_get_action_link(
                'view') or event.employee_id and event.employee_id._notify_get_action_link('view') or None
            partner_name = event.contact_id and event.contact_id.name or event.employee_id and event.employee_id.name or None
        # generate html code for door link
        door_link = door_link and Markup('<a href="%s">%s</a>') % (door_link, event.door_id.name) or None
        # generate controller link
        controller_link = controller_link and Markup('<a href="%s">%s</a>') % (controller_link, event.controller_id.name) or None
        # generate webstack link
        webstack_link = webstack_link and Markup('<a href="%s">%s</a>') % (webstack_link, event.webstack_id.name) or None
        # generate html code for partner link
        partner_link = partner_link and Markup('<a href="%s">%s</a>') % (partner_link, partner_name) or None
        # generate html code for event link
        event_link = event_link and Markup('<a href="%s">%s</a>') % (
        event_link, event.name if not is_system_event else event.error_description) or event.name
        # event_time is already in UTC and is a datetime object
        event_time = getattr(event, 'timestamp', None) or getattr(event, 'event_time', None)
        datetime_in_partner_tz = event_time
        datetime_in_partner_tz_naive = event_time
        if event_time:
            user_tz = partner_id.tz or 'UTC'
            local_tz = timezone(user_tz)
            datetime_utc = event_time.replace(tzinfo=UTC)
            datetime_in_partner_tz = datetime_utc.astimezone(local_tz)

            # Optionally, to return the datetime without timezone information:
            datetime_in_partner_tz_naive = datetime_in_partner_tz.replace(tzinfo=None)

        notify_message = Markup("<h5>%s</h5><p>%s</p><p>%s</p>") % (
            _('RFID Notification for %s', event_link),
            _('Where: %s', door_link or controller_link or webstack_link),
            _('When: %s', datetime_in_partner_tz_naive),
        )
        notify_message += Markup("<p>%s</p>") % (
            _('Who: %s', partner_link)
        ) if partner_link else ''
        return notify_title, notify_message

    def generate_recipients(self):
        self.ensure_one()
        recipients = self.notify_partner_ids
        recipients += self.zone_id.message_follower_ids.partner_id if self.notify_followers else self.env['res.partner']
        return recipients
    def process_event(self, event):
        for notification in self:
            if notification.user_event == event.event_action or notification.system_event == event.event_action:
                recipients = notification.generate_recipients()
                for recipient in recipients:
                    notify_title, notify_message = self.with_context(lang=recipient.lang).make_message(
                        event, partner_id=recipient)
                    if notification.notification_type == 'discuss' and recipient.user_ids:
                        notification.notify_by_discuss([recipient], notify_message)
                    elif notification.notification_type == 'email':
                        notification.notify_by_email([recipient], notify_title, notify_message)
                    elif notification.notification_type == 'sms':
                        pass

    def notify_by_discuss(self, recipients, msg):
        odoobot_id = self.env.ref("base.partner_root").id
        for recipient in recipients:
            partners_to = [recipient.id]
            channel = self.env["discuss.channel"].with_user(SUPERUSER_ID).channel_get(partners_to)
            channel.message_post(body=msg, author_id=odoobot_id, message_type="comment",
                                 subtype_xmlid="mail.mt_comment")

    def notify_by_email(self, recipients, subject, body):
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

    def notify_by_sms(self, recipients, msg):
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

    @api.constrains('notify_partner_ids', 'notification_type', 'notify_followers')
    def check_recipients(self):
        for notification in self:
            recipients = notification.generate_recipients()
            if not recipients:
                raise UserError(_('No recipients for %s notification!', notification.name))
            if notification.notification_type == 'discuss':
                for recipient in recipients:
                    if not recipient.user_ids:
                        raise UserError(_('Recipient %s has no user account in %s!', recipient.name, notification.name))
            elif notification.notification_type == 'email':
                for recipient in recipients:
                    if not recipient.email:
                        raise UserError(_('Recipient %s has no email address in %s!', recipient.name, notification.name))
            elif notification.notification_type == 'sms':
                pass
