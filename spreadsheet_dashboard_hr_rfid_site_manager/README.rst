=================================
Access Control Dashboard - Sites
=================================

Bridge between the access-control dashboards and the Site Manager. When both
are installed, the *Access Control* and *Security and Devices* boards in the
Dashboards app gain an interactive **Site** filter, so every KPI and chart can
be narrowed to one physical site (office, plant, warehouse...).

Overview
========

* Adds a *Site* global filter next to Period / Company / Door on the
  Access Control board (access events carry the site of their door).
* Adds the same filter to the Security and Devices board (system events reach
  the site through their door).

Configuration
=============

None. The module installs automatically when both ``spreadsheet_dashboard_hr_rfid``
and ``hr_rfid_site_manager`` are present. Assign doors to sites in Site Manager
and the filter is ready.

Technical
=========

Replaces the two shipped ``spreadsheet.dashboard`` documents with site-enabled
variants (same boards + one extra global filter wired via ``site_id`` /
``door_id.site_id``). No models, no views.

Credits
=======

* Polimex Holding Ltd. <https://polimex.co>
