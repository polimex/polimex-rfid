.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

====================
HR RFID Site Manager
====================

Groups access-control equipment into a tree of sites, so a building, a floor
and a room are records an operator can open, instead of a flat list of
webstacks, controllers and doors.

Configuration
-------------

No configuration is required. The module adds a Site Manager menu; create the
first site and attach webstacks, controllers or doors to it.

A site can create its own access group (the *Make access group* option), so
granting somebody the whole building is one assignment rather than one per
door.

Usage
-----

Open RFID System > Hardware Manager > Site Manager. Each site shows what
is attached to it - webstacks, controllers, doors, access groups and alarm
line groups - with the counts of everything below it in the tree, and its
own state.

Sites nest: a child site's doors are counted on its parent as well, so the
top of the tree answers "how much equipment does this building hold".

Contributors
------------

Polimex Holding Development team

Maintainer
----------

.. image:: https://raw.githubusercontent.com/polimex/logos/5c5af675ad5d6ef12bb29664c250196c51ac2bc8/company_logo.png
   :alt: Polimex Logo
   :target: https://polimex.co

This module is created and maintained by the Polimex Dev Team.
