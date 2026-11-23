# Introduction
This module extends the RFID Access Control (hr_rfid) module, allowing it to import user data from Windows based Andromeda Access Control System by Polimex

# Features
* Import all Users and cards.
* Import All Access Control Groups.
* Import all Access Users Rights.

# Running the import again

The import can be run as often as you like. Everything it creates is marked
with the Andromeda record it came from, so a later run finds that work instead
of doing it a second time:

- Somebody already imported is not offered in the list again.
- A company, a department, a person or a card that is already here is used as
  it is - no second copy is made.
- An access group somebody already has is not given to them again.
- A card that was switched off in Andromeda is not handed out again as a
  working one.

Nothing is deleted and nothing already corrected here is overwritten: a name
you have put right in Odoo stays as you left it.

**One thing to check first.** Databases filled by a version of this import from
before August 2026 were marked in a different way, which the current version
does not read. On such a database the people imported back then are offered
again and would come in as new records. If you are not sure which case you are
in, import one person first and see whether a second copy appears before doing
the rest.

# Requirements

* System packs

```console
sudo apt install libfbclient2
```


* PIP envirement

```code
pip install fdb
```
