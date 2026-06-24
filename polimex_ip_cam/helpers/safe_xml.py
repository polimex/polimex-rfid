"""Hardened XML parsing for untrusted input.

Cameras, network discovery responders and the public ANPR webhook all hand us
XML we did not produce. Parsing it must never allow XXE (external entity
injection), entity-expansion DoS ("billion laughs") or external-DTD/SSRF.

We get exactly that from ``lxml`` — a hard Odoo dependency, always installed —
configured the same way Odoo core parses untrusted XML: ``resolve_entities=False``
(see ``odoo/tools/misc.py`` which even sets it as the global default parser, and
``odoo/tools/xml_utils.py``). This removes the need for the external
``defusedxml`` package.
"""
import xml.etree.ElementTree as _stdlib_ET

from lxml import etree


def _safe_parser():
    """Build a hardened lxml parser.

    A fresh parser per call (matching ``odoo/tools/xml_utils.py``): lxml parsers
    are not thread-safe and discovery parses replies from worker threads.

    - ``resolve_entities=False`` — entities are never expanded: no XXE and no
      billion-laughs entity-expansion DoS.
    - ``no_network=True`` — never fetch external DTDs/entities (no SSRF).
    - ``remove_comments`` / ``remove_pis`` — keep the tree shape the simple tag
      walkers expect: stdlib ElementTree drops comments/PIs, lxml keeps them
      unless told otherwise (a stray comment node has a callable ``.tag`` that
      would break ``tag.split`` / ``tag.rsplit`` walkers).
    """
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        remove_comments=True,
        remove_pis=True,
    )


def parse_untrusted_xml(data):
    """Safely parse untrusted XML and return an ``lxml.etree._Element``.

    Accepts ``str`` or ``bytes``. A ``str`` is encoded to bytes first because
    lxml refuses to parse a ``str`` that carries an XML encoding declaration.
    Raises ``lxml.etree.XMLSyntaxError`` on malformed/empty input.
    """
    if isinstance(data, str):
        data = data.encode()
    return etree.fromstring(data or b"", parser=_safe_parser())


def parse_untrusted_xml_stdlib(data):
    """Safely parse untrusted XML and return a stdlib ``ElementTree.Element``.

    For read-modify-write flows that must stay on stdlib ElementTree because the
    parsed tree is mutated and re-serialised to a device that expects a specific
    namespace layout (the Hikvision ``register_namespace('', ...)`` trick).

    The lxml pass leaves entity references un-expanded (no XXE / no billion
    laughs). Re-serialising and re-parsing with stdlib ElementTree then fails on
    any dangling entity reference (a legitimate device config has none), which
    the read-modify-write caller treats as "unparseable" and rebuilds the config
    from scratch — so a hostile payload neither leaks nor survives.

    Raises ``xml.etree.ElementTree.ParseError`` or ``lxml.etree.XMLSyntaxError``
    on malformed / entity-bearing input.
    """
    return _stdlib_ET.fromstring(etree.tostring(parse_untrusted_xml(data)))
