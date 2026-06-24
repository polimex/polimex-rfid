# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import xml.etree.ElementTree as STD

from lxml import etree

from odoo.tests import TransactionCase, tagged
from odoo.addons.polimex_ip_cam.helpers.safe_xml import (
    parse_untrusted_xml,
    parse_untrusted_xml_stdlib,
)

# A classic XXE probe: a SYSTEM entity pointing at a local file. A vulnerable
# parser would inline the file's content into <v>.
_XXE = (
    b'<?xml version="1.0"?>'
    b'<!DOCTYPE r [ <!ENTITY xxe SYSTEM "file:///etc/hostname"> ]>'
    b'<r><v>&xxe;</v></r>'
)


@tagged("post_install", "-at_install", "polimex_ip_cam", "ipcam_xxe")
class TestSafeXml(TransactionCase):
    """The untrusted-XML helper must neutralise XXE, entity-expansion and
    external-DTD attacks — the protection we used to get from defusedxml,
    now from lxml configured like Odoo core (resolve_entities=False)."""

    def test_xxe_external_entity_not_resolved(self):
        root = parse_untrusted_xml(_XXE)
        # The external entity must NOT be expanded -> nothing reaches <v>.
        self.assertFalse(
            (root.find("v").text or "").strip(),
            "External entity was expanded -> XXE not blocked",
        )

    def test_billion_laughs_not_expanded(self):
        # Entity-expansion DoS: with resolve_entities=False nothing expands.
        lol = (
            b'<?xml version="1.0"?>'
            b'<!DOCTYPE l ['
            b' <!ENTITY a "AAAAAAAAAA">'
            b' <!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">'
            b' <!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">'
            b' ]>'
            b'<r>&c;</r>'
        )
        root = parse_untrusted_xml(lol)
        # '&c;' would inflate to 1000 'A's if expanded; it must stay a reference.
        self.assertLess(
            len(etree.tostring(root)), 200,
            "Entities were expanded -> billion-laughs not blocked",
        )

    def test_well_formed_xml_still_parses(self):
        root = parse_untrusted_xml(b"<r><a>x</a><b>y</b></r>")
        self.assertEqual(root.find("a").text, "x")
        self.assertEqual(root.find("b").text, "y")

    def test_str_with_encoding_declaration(self):
        # lxml refuses a str carrying an encoding declaration; the helper must
        # encode to bytes first so cameras/discovery that send a decoded str
        # (e.g. SADP replies) still parse.
        root = parse_untrusted_xml('<?xml version="1.0" encoding="UTF-8"?><r>ok</r>')
        self.assertEqual(root.text, "ok")

    def test_malformed_and_empty_raise_xmlsyntaxerror(self):
        with self.assertRaises(etree.XMLSyntaxError):
            parse_untrusted_xml(b"<r><unclosed>")
        with self.assertRaises(etree.XMLSyntaxError):
            parse_untrusted_xml(b"")
        with self.assertRaises(etree.XMLSyntaxError):
            parse_untrusted_xml(None)

    def test_comments_and_pis_stripped(self):
        # The tag walkers (anpr parse_xml_to_dict, discovery _local_text) iterate
        # children and call tag.split/.rsplit; comment/PI nodes — whose .tag is a
        # callable in lxml — must not leak into the tree.
        root = parse_untrusted_xml(b"<r><!-- c --><?pi x?><a>1</a></r>")
        self.assertEqual([child.tag for child in root], ["a"])

    def test_stdlib_variant_returns_stdlib_and_rejects_entities(self):
        # A legitimate (entity-free) config -> clean stdlib ElementTree element.
        root = parse_untrusted_xml_stdlib(b"<r><a>1</a></r>")
        self.assertIsInstance(root, STD.Element)
        self.assertEqual(root.find("a").text, "1")
        # A hostile XXE payload -> rejected (the un-expanded entity reference is
        # a dangling reference once re-serialised), so the read-modify-write
        # caller falls back to rebuilding the config from scratch (no leak/DoS).
        with self.assertRaises(STD.ParseError):
            parse_untrusted_xml_stdlib(_XXE)
