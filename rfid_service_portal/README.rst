====================
RFID Services Portal
====================

Overview
========

The portal side of RFID Services. A customer who was sold a service at the
till and has a portal login sees their services under **RFID Services** in
the portal, and the cashier can send the customer the badge or a portal
invitation from the sale form.

It adds nothing to configure and is installed automatically when both RFID
Services (``rfid_service_base``) and the RFID portal (``hr_rfid_portal``)
are installed.

Configuration
=============

Nothing to configure. The customer needs a portal login to see the list of
their services; the cashier can send the invitation while selling (see
Usage).

Usage
=====

For the customer
----------------

* The portal home page shows the card **RFID Services** with the number of
  services sold to the customer.
* **RFID Services** lists them, the newest first: the reference of the sale,
  the service, from when and until when it is valid, the visits counted on it
  and its state (Registered, Active, Finished or Canceled). The hours are
  shown on the customer's own clock.
* A badge shared with the customer opens as a page with the barcode of the
  card and the period the card is valid for. The link carries its own access
  key, so it opens without a login.

For the cashier
---------------

On the sale form of a service:

* **Invite in Portal**, next to the e-mail: when ticked, the customer gets an
  invitation to the portal by e-mail as soon as the sale is confirmed. The
  box appears once an e-mail is filled in.
* **Share**: confirms the sale and opens the sharing dialog, with the
  customer already chosen, to send them the link to their badge. It is shown
  for services that issue a barcode card, once an e-mail or a phone number is
  filled in, and it needs the e-mail.

Technical
=========

* ``/my/rfid_services`` (login required) - the sales of the logged-in user's
  contact (``rfid.service.sale`` by ``partner_id``).
* ``/my/rfid_service<card id>`` - the badge page of a card
  (``hr_rfid_portal.portal_my_barcode``) for whoever holds the card's access
  token. The link **Share** sends is the RFID portal's own
  (``/my/webcard/<card id>``, with the same token).
* ``rfid.service.sale.wiz`` gains ``invite_in_portal`` and ``share_card``;
  the invitation is core's portal access wizard (``portal.wizard.user``,
  ``action_grant_access``).
* The demo data gives the demo login a badge and a service that has ended;
  the RFID Demo Data module (``hr_rfid_demo``) keeps a running one next to
  it.

Credits
=======

Authors
-------

* Polimex Dev Team

Maintainers
-----------

This module is maintained by Polimex Holding Ltd. - https://polimex.co
