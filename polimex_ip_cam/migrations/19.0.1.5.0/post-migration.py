import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Collapse the legacy 5-bucket list_category down to the two buckets the
    camera hardware actually supports: whitelist (allow) and blacklist (deny).

    The dropped buckets ('graylist', 'yellolist', 'otherlist') were never
    auto-grant lists, so they are remapped to 'blacklist' as a FAIL-SAFE
    default: only an explicit whitelist may grant access, and every ambiguous
    legacy bucket therefore collapses to deny. An operator who wants a
    different outcome for a specific plate can simply re-classify it as
    whitelist after the upgrade.
    """
    if not version:
        return
    cr.execute(
        """
        UPDATE cctv_camera_rfid_rel
           SET list_category = 'blacklist'
         WHERE list_category IN ('graylist', 'yellolist', 'otherlist')
        """
    )
    migrated = cr.rowcount
    _logger.info(
        "polimex_ip_cam: remapped %s legacy list_category row(s) "
        "(graylist/yellolist/otherlist) to 'blacklist' (fail-safe deny).",
        migrated,
    )
