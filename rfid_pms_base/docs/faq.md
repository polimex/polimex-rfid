## The setup checklist (onboarding banner)

The banner is NOT a view class of this module. It is attached by putting the
onboarding's `route_name` in the CONTEXT of the action:

```xml
<field name="context">{'onboarding_route_name': 'rfid_pms_base_setup'}</field>
```

on ``action_window_room` (Hotel Rooms, kanban/list/form)` (`views/room.xml`). That is the whole integration on this side.

Everything else lives in `hr_rfid`: the `OnboardingBanner` OWL component, the
extension of the stock `web.ListView` / `web.KanbanView` templates, and the two
server methods `onboarding.onboarding.get_onboarding_panel_html(route_name)` /
`close_onboarding_panel(route_name)` - which render and close core's own
`onboarding.onboarding_panel` template, so the banner is identical to Odoo's
native one and translated server-side.

**Do not go back to `js_class`.** It was one until August 2026, and a view
carries exactly ONE `js_class`: `hr_rfid_refresh_views` (auto_install, so on
nearly every database) writes its own over the view it inherits, and the banner
component was then never created at all - no error, no request, no banner, with
the server side rendering perfectly the whole time. Keying on the action context
removes the conflict: the view can carry any `js_class` and still show the
banner.

This module's own part is `models/onboarding_onboarding.py`:
`_prepare_rendering_values` auto-completes its two steps (an `hr.rfid.access.group` with doors exists; a `rfid_pms_base.room` exists) for the CURRENT company
before delegating to core, and `action_close_panel_pms_setup` is the close action named on the
onboarding record. Nothing here has to know how the banner is drawn.
