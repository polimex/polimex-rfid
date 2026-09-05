import json

from odoo import api, fields, models
from odoo.exceptions import UserError


class HwImportGroupMergeWiz(models.TransientModel):
    _name = 'hr.rfid.hw.import.group.merge.wiz'
    _description = 'Merge proposed access groups'

    run_id = fields.Many2one('hr.rfid.hw.import.run', required=True, ondelete='cascade',
                             help="The survey the groups belong to.")
    group_ids = fields.Many2many('hr.rfid.hw.import.group', string='Groups to merge',
                                 help="The proposed groups that become one.")
    name = fields.Char(required=True, help="Name of the merged group.")
    warning = fields.Text(compute='_compute_warning',
                          help="What the merge changes: every card of the merged group receives every right of it.")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        ids = self.env.context.get('active_ids') or []
        if self.env.context.get('active_model') == 'hr.rfid.hw.import.group' and ids:
            groups = self.env['hr.rfid.hw.import.group'].browse(ids)
            values.setdefault('run_id', groups[0].run_id.id)
            values.setdefault('group_ids', [(6, 0, groups.ids)])
            values.setdefault('name', groups[0].name)
        return values

    @api.model
    def _why_not(self, groups):
        """Why these groups cannot become one, in the operator's words; empty
        when they can.

        The access control module gives a person the rights of every group
        they are in, and holds ONE right per door in a group and ONE way to a
        door per person. A merge that breaks either of those would be refused
        by that module later, with a message about a person - so it is refused
        here, with the reason.
        """
        reasons = []
        cards = groups.mapped('card_ids')
        twin = self.env['hr.rfid.hw.import.group'].search([
            ('run_id', '=', groups[0].run_id.id), ('holder_key', '=', groups._holder_key_for(cards)),
            ('id', 'not in', groups.ids)], limit=1)
        if twin:
            reasons.append(self.env._(
                "The cards of these groups together are exactly the cards of '%(name)s'. Include that "
                "group in the merge as well.", name=twin.name))
        rights = groups.mapped('right_ids')
        by_door = {}
        for right in rights:
            by_door.setdefault((right.ctrl_id, right.door_number), set()).add((right.ts_number, right.alarm))
        clashing = [right for right in rights if len(by_door[(right.ctrl_id, right.door_number)]) > 1]
        if clashing:
            doors = sorted({r.door_label for r in clashing})
            reasons.append(self.env._(
                "These groups open %(doors)s on different schedules or with different alarm rights; "
                "a group holds one right per door.", doors=', '.join(doors)))
        merged_doors = set(by_door)
        twice = {}
        for card in cards:
            for other in card.group_ids - groups:
                for right in other.right_ids:
                    if (right.ctrl_id, right.door_number) in merged_doors:
                        twice.setdefault(card.number_display, set()).add(right.door_label)
        for number, doors in sorted(twice.items()):
            reasons.append(self.env._(
                "Card %(number)s would reach %(doors)s through two groups; that is not allowed.",
                number=number, doors=', '.join(sorted(doors))))
        return reasons

    @api.depends('group_ids')
    def _compute_warning(self):
        for wiz in self:
            groups = wiz.group_ids
            if len(groups) < 2:
                wiz.warning = self.env._("Choose at least two groups.")
                continue
            reasons = self._why_not(groups)
            if reasons:
                wiz.warning = self.env._("These groups cannot be merged:") + '\n' + '\n'.join(reasons)
                continue
            all_cards = groups.mapped('card_ids')
            all_rights = groups.mapped('right_ids')
            extra = []
            for group in groups:
                gained = all_rights - group.right_ids
                if gained:
                    extra.append(self.env._(
                        "%(cards)s cards of '%(group)s' will also open: %(doors)s",
                        cards=len(group.card_ids), group=group.name,
                        doors=', '.join(gained.mapped('door_label'))))
            wiz.warning = '\n'.join(extra) or self.env._("The groups already give the same rights.")
            wiz.warning += '\n' + self.env._("The merged group will have %(cards)s cards and %(doors)s doors.",
                                             cards=len(all_cards), doors=len(all_rights))

    def action_merge(self):
        self.ensure_one()
        groups = self.group_ids
        if len(groups) < 2:
            raise UserError(self.env._("Choose at least two groups to merge."))
        reasons = self._why_not(groups)
        if reasons:
            raise UserError(self.env._("These groups cannot be merged:") + '\n' + '\n'.join(reasons))
        keep = groups.sorted('sequence')[0]
        others = groups - keep
        cards = groups.mapped('card_ids')
        merged = json.loads(keep.merged_from_json or '[]') + [g.name for g in others]
        for group in others:
            group.right_ids.write({'group_id': keep.id})
            group.unlink()
        keep.write({
            'name': (self.name or keep.name)[:32],
            'card_ids': [(6, 0, cards.ids)],
            'holder_key': self.env['hr.rfid.hw.import.group']._holder_key_for(cards),
            'merged_from_json': json.dumps(merged),
        })
        return {'type': 'ir.actions.act_window_close'}
