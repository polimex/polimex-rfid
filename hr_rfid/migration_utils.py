# Polimex Holding Ltd. - https://polimex.co
"""Shared migration helper: put demo records back under the noupdate flag.

Odoo core marks EVERY demo record ``noupdate=True``
(``modules/loading.py``: ``convert_file(..., noupdate=kind == 'demo')``) so that
an upgrade never rewrites nor garbage-collects data the users of a demo instance
have been touching. A ``<data noupdate="False">`` in a demo file OVERRIDES that
default (``tools/convert.py``: the ``<data>`` attribute wins over the caller's
value) and opts the records out of the protection.

The cost surfaces only on a database that has STOPPED reloading demo - which
happens by itself, since Odoo clears ``ir_module_module.demo`` whenever a demo
load fails once. From then on the demo xml ids are absent from
``pool.loaded_xmlids``, so ``ir.model.data._process_end`` reads them as
"removed from the module" and DELETES the records. When live data references
one of them through a RESTRICT foreign key (a sold service, an event on a door)
the delete raises, the whole registry load is rolled back and the module can no
longer be upgraded at all.

Fixing the XML only helps databases that still read the file. On the ones that
do not, ``ir_model_data.noupdate`` is already stored as false and nothing would
ever correct it - hence this back-fill, which each affected module calls from
its ``pre-migrate`` (it must run before ``_process_end``, at the end of the
load). Raw SQL is deliberate: ``ir.model.data`` is being repaired underneath the
ORM, and the ids come from the module's own manifest, not from the database.
"""
import logging
import os

from lxml import etree

from odoo.modules.module import get_manifest, get_module_path

_logger = logging.getLogger(__name__)


def _demo_xml_ids(module):
    """Every xml id declared by the module's own demo files."""
    module_path = get_module_path(module)
    if not module_path:
        _logger.warning(
            "Module %s not found on the addons path; demo noupdate back-fill "
            "skipped", module)
        return []

    names = []
    for filename in get_manifest(module).get("demo", []):
        path = os.path.join(module_path, filename)
        if not os.path.exists(path):
            _logger.warning("%s: demo file %s is declared but missing",
                            module, filename)
            continue
        try:
            tree = etree.parse(path)
        except etree.XMLSyntaxError:
            _logger.warning("%s: demo file %s does not parse; skipped",
                            module, filename, exc_info=True)
            continue
        for element in tree.iter():
            xml_id = element.get("id")
            # A dotted id belongs to another module and is only referenced
            # here, so it is not this module's ir.model.data row to repair.
            if xml_id and "." not in xml_id:
                names.append(xml_id)
    return names


def demo_records_to_noupdate(cr, module):
    """Set ``noupdate`` on the module's demo ir.model.data rows.

    Idempotent: only rows still marked updatable are touched.
    """
    names = _demo_xml_ids(module)
    if not names:
        return 0

    cr.execute(
        """UPDATE ir_model_data
              SET noupdate = true
            WHERE module = %s
              AND name IN %s
              AND COALESCE(noupdate, false) = false""",
        (module, tuple(names)),
    )
    if cr.rowcount:
        _logger.info(
            "%s: %s demo records put back under noupdate - an upgrade will no "
            "longer try to delete them", module, cr.rowcount)
    return cr.rowcount
