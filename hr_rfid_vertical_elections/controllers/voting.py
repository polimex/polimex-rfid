# -*- coding: utf-8 -*-

from datetime import datetime
from werkzeug import exceptions

from odoo import http
from odoo.http import request

class VoteController(http.Controller):

    # ------
    # ROUTES
    # ------

    @http.route("/voting_display/<string:short_code>/voting", type="http", auth="public", website=True)
    def voting_main(self, short_code):
        display_sudo = request.env["voting.display"].sudo().search([("short_code", "=", short_code)])
        if not display_sudo:
            raise exceptions.NotFound()
        return request.render("hr_rfid_vertical_elections.voting_display", {"display": display_sudo})

    @http.route("/voting_display/<string:access_token>/background", type="http", auth="public")
    def display_background_image(self, access_token):
        display_sudo = self._fetch_display_from_access_token(access_token)
        if not display_sudo.display_background_image:
            return ""
        return request.env['ir.binary']._get_image_stream_from(display_sudo, "display_background_image").get_response()


    @http.route("/voting_display/<string:access_token>/get_existing_sessions", type="json", auth="public")
    def get_existing_sessions(self, access_token):
        display_sudo = self._fetch_display_from_access_token(access_token)
        return request.env["voting.session"].sudo().search_read(
            [("display_id", "=", display_sudo.id), ("planned_date", "=", datetime.today())],
            ["name", "create_uid", "planned_date", "start_datetime", "end_datetime", "state",
             'voting_time', 'vote_results_time', 'vote_total', 'vote_yes', 'vote_no', 'vote_abstain', 'final_vote'],
            order="start_datetime asc",
        )

    @http.route("/voting_display/<string:access_token>/session/<int:session_id>/close", type="json", auth="public")
    def session_close(self, access_token, session_id, **kwargs):
        fields_allowlist = {"state", "end_datetime"}
        session_id =  self._fetch_sessions(session_id, access_token)
        fields_dict = {field: kwargs[field] for field in fields_allowlist if kwargs.get(field)}
        fields_dict["end_datetime"] = datetime.now()
        result = session_id.write(fields_dict)
        session_id.message_post(body="Session closed from display.")
        return result

    # ------
    # TOOLS
    # ------

    def _fetch_sessions(self, display_id, access_token):
        """Return the sudo-ed booking if it takes place in the room corresponding
        to the given access token
        """
        display_sudo = self._fetch_display_from_access_token(access_token)
        session_sudo = display_sudo.voting_session_ids.filtered_domain([('id', '=', display_id)])
        if not session_sudo:
            raise exceptions.NotFound()
        return session_sudo

    def _fetch_display_from_access_token(self, access_token):
        """Return the sudo-ed record of the display corresponding to the given
        access token
        """
        display_sudo = request.env["voting.display"].sudo().search([("access_token", "=", access_token)])
        if not display_sudo:
            raise exceptions.NotFound()
        return display_sudo
