odoo.define('hr_rfid_webstack.action_button', function (require) {
    "use strict";
    var core = require('web.core');
    var ListController = require('web.ListController');
    var rpc = require('web.rpc');
    var session = require('web.session');
    var _t = core._t;
    ListController.include({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            if (this.$buttons) {
                this.$buttons.find('.oe_action_button_discovery').click(this.proxy('action_discovery'));
                this.$buttons.find('.oe_action_button_manual').click(this.proxy('action_manual_add'));
            }
        },
        action_manual_add: function () {
            var self = this
            var user = session.uid;
            self.do_action({
                    name: _t('Modules Manual Add'),
                    type: 'ir.actions.act_window',
                    res_model: 'hr.rfid.webstack.manual.create',
                    view_id: 'hr_rfid_webstack_manual_create_wiz',
                    views: [[false, 'form']],
                    view_mode: 'form',
                    view_type: 'form',
                    target: 'new',
            });
            window.location
        },
       action_discovery: function () {
            var self = this
            var user = session.uid;
            self.do_action({
                    name: _t('Modules Discovery'),
                    type: 'ir.actions.act_window',
                    res_model: 'hr.rfid.webstack.discovery',
                    view_id: 'hr_rfid_webstack_discovery_wiz',
                    views: [[false, 'form']],
                    view_mode: 'form',
                    view_type: 'form',
                    target: 'new',
            });
            window.location
        },
    });
})