---
id: hr_rfid_vertical_elections
title: RFID Elections
module: hr_rfid_vertical_elections
module_version: 19.0.1.6.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: HR RFID Vertical Elections
last_updated: '2026-08-14'
source_digest: sha256:7d35422a10a83a49a29b86c886b6f82aa8f83f7094c61bf681be937896d052ac
depends:
- hr_rfid
- bus
- onboarding
entities:
  primary: hr.rfid.event.user
  related:
  - hr.rfid.workcode
  - onboarding.onboarding
  - onboarding.onboarding.step
  - voting.vote
  - voting.display
  - voting.item
  - voting.participants
  - voting.session
keywords:
- elections
- event
- onboarding
- rfid
- step
- user
- vertical
- vote
- voting
- workcode
license: AGPL-3
author: Polimex Dev Team
category: Human Resources
installable: true
application: true
auto_install: false
counts:
  models: 9
  views: 14
  access_rules: 5
  record_rules: 2
  crons: 0
  images: 2
images:
- path: static/description/icon.png
  sha256: sha256:6202c26e4d51f1810eea610ce879ad761ff0ed801f39a3d74b446f41f6bc4a1c
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/description/icon.svg
  sha256: sha256:5866ebc806dfb47cde3f3712d71ec80b71694a95324560b57096d7f7e1303c10
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# RFID Elections — `hr_rfid_vertical_elections` v19.0.1.6.0

HR RFID Vertical Elections

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview — module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_rfid_vertical_elections`
- **Version**: `19.0.1.6.0`
- **Category**: Human Resources
- **License**: AGPL-3
- **Author**: Polimex Dev Team
- **Application**: yes
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `hr_rfid`, `bus`, `onboarding`

### README (verbatim)

#### RFID Elections

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-18.0.1.0.0-green.svg)](https://apps.odoo.com)

Electronic voting system using RFID cards for secure, transparent elections.

##### 🎯 Overview

RFID Elections transforms traditional voting into a modern, secure electronic process using RFID technology. Perfect for corporate elections, board meetings, shareholder voting, and any scenario requiring authenticated, auditable voting with real-time results.

##### ✨ Key Features

###### Voting System
- **RFID Authentication**: Secure voter identification
- **Secret Ballot**: Anonymous voting options
- **Real-time Results**: Instant vote counting
- **Multiple Sessions**: Concurrent voting sessions

###### Election Management
- **Session Control**: Start/stop voting periods
- **Participant Management**: Voter registration and validation
- **Voting Items**: Multiple questions per session
- **Result Display**: Live results on displays

###### Security Features
- **One Person, One Vote**: Duplicate prevention
- **Audit Trail**: Complete voting history
- **Encrypted Storage**: Secure vote recording
- **Access Control**: Role-based permissions

###### Display System
- **Public Displays**: Real-time result boards
- **Vote Progress**: Live participation rates
- **Winner Announcement**: Automatic determination
- **Multi-screen Support**: Distributed displays

##### 📋 Requirements

- Odoo 18.0+
- hr_rfid module
- RFID readers at voting stations
- Display screens (optional)

###### Dependencies
```python
'depends': ['hr_rfid', 'website']
```

##### 🛠️ Installation

1. Install hr_rfid module first

2. Install the elections module:
```bash
./odoo-bin -d your_database -i hr_rfid_vertical_elections
```

3. Configure voting stations and displays

##### 🔧 Configuration

###### Voting Station Setup

1. **RFID Readers**
   - Assign readers as voting stations
   - Configure workcode for voting
   - Set station location/name

2. **Display Screens**
   - Create display records
   - Generate display URLs
   - Configure refresh rates
   - Set display layouts

###### Election Configuration

1. **Create Session**
   - Name and description
   - Start/end times
   - Voting rules (secret/public)
   - Participant list

2. **Add Voting Items**
   - Question text
   - Answer options
   - Vote type (yes/no, multiple choice)
   - Required majority

3. **Register Participants**
   - Import from employees
   - Add external participants
   - Assign RFID cards
   - Set voting rights

##### 📖 Usage

###### Running an Election

1. **Preparation**
   - Create voting session
   - Add all voting items
   - Register participants
   - Test voting stations

2. **Start Voting**
   - Activate session
   - Open voting stations
   - Monitor participation
   - Display live results

3. **Voting Process**
   - Participant scans RFID card
   - System validates eligibility
   - Shows voting items
   - Records vote securely

4. **End Session**
   - Close voting
   - Finalize results
   - Generate reports
   - Archive session

###### Voter Experience

1. **Approach Station**
   - Scan RFID card
   - Wait for validation
   - See welcome message

2. **Cast Votes**
   - View each item
   - Select choice
   - Confirm vote
   - See confirmation

3. **Completion**
   - Vote recorded message
   - Thank you screen
   - Automatic logout

##### 📊 Result Management

###### Real-time Display
```
Current Voting Session: Board Elections 2024

Item 1: Approve Annual Budget
Yes: 145 (72.5%)  [████████████████░░░░]
No:   55 (27.5%)  [█████░░░░░░░░░░░░░░░]
Participation: 200/250 (80%)

Item 2: Elect Board Chairman
John Doe:    89 (44.5%)  [████████░░░░░░░░]
Jane Smith:  76 (38.0%)  [███████░░░░░░░░░]
Bob Wilson:  35 (17.5%)  [███░░░░░░░░░░░░░]
```

###### Reports Available
- Detailed results by item
- Participation statistics
- Timeline of votes
- Audit trail report

##### 🖥️ Display System

###### Display Types

1. **Result Board**
   - Live vote counts
   - Percentage bars
   - Winner indication
   - Auto-refresh

2. **Participation Monitor**
   - Total voters
   - Votes cast
   - Remaining voters
   - Time remaining

3. **Winner Announcement**
   - Final results
   - Winner declaration
   - Official stamp
   - QR code verification

###### Display URLs
```
#### Main results display
https://your-odoo.com/voting/display/main

#### Participation monitor
https://your-odoo.com/voting/display/participation

#### Mobile-friendly view
https://your-odoo.com/voting/display/mobile
```

##### 🔒 Security & Compliance

###### Security Measures
- **Encrypted Votes**: AES-256 encryption
- **Tamper Detection**: Hash verification
- **Access Logs**: Complete audit trail
- **Time Stamps**: Blockchain-ready

###### Compliance Features
- **Anonymous Voting**: When required
- **Proxy Voting**: Delegation support
- **Quorum Tracking**: Minimum participation
- **Legal Reports**: Compliance documentation

##### 🔌 API Integration

###### External Integration
```python
#### Webhook for vote cast
@http.route('/voting/webhook/vote', type='json', auth='public')
def vote_webhook(self, session_id, vote_data):
    # Process external vote
    # Validate and record
    return {'status': 'recorded', 'id': vote_id}
```

###### Result Export
```python
#### Export results via API
@http.route('/voting/api/results/<int:session_id>', 
            type='json', auth='api_key')
def get_results(self, session_id):
    session = request.env['voting.session'].browse(session_id)
    return {
        'session': session.name,
        'items': session.get_results_json(),
        'participation': session.participation_rate,
    }
```

##### 🐛 Troubleshooting

###### Common Issues

1. **Card not recognized**
   - Check participant registration
   - Verify card is active
   - Test reader connection

2. **Vote not recording**
   - Check session is active
   - Verify voting rights
   - Review error logs

3. **Display not updating**
   - Check network connection
   - Verify display URL
   - Clear browser cache

###### Debug Mode
```python
#### Enable debug logging
voting_debug = True
log_all_votes = True
```

##### ⚙️ Advanced Features

###### Weighted Voting
```python
#### Shareholders with different weights
participant.vote_weight = shares_owned
```

###### Delegation/Proxy
```python
#### Allow vote delegation
participant.delegate_to = proxy_participant
```

###### Multi-round Voting
- Elimination rounds
- Runoff elections
- Ranked choice voting

##### 🤝 Contributing

We welcome contributions:
1. Fork repository
2. Add voting features
3. Test with mock elections
4. Submit pull request

##### 📄 License

Licensed under AGPL-3.0. See [LICENSE](../LICENSE) for details.

##### 👥 Credits

###### Authors
- Polimex Dev Team

###### Maintainer
- [Polimex](https://polimex.co)

##### 🌐 Links

- [Documentation](https://polimex.co/docs/rfid-elections)
- [Demo Video](https://polimex.co/videos/rfid-voting)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/hr_rfid_vertical_elections/)

---

For more information, visit [polimex.co](https://polimex.co)


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i hr_rfid_vertical_elections --stop-after-init
```

> **Application**: this module will appear as a top-level app in the Apps menu.


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `hr.rfid.event.user` <a id='model-hr-rfid-event-user'></a>
Python class `HrRfidUserEvent` in `models/hr_rfid_event_user.py:6`.  Model.  Inherits: `hr.rfid.event.user`.

#### Notable methods

- **`create(self, vals_list)`** — decorators: `@api.model_create_multi`
  - super-split (super `create`): pre=— · post=`log_info`
  - effects: `log_info`
  - touches: `voting.session`, `voting.vote`
- **`re_vote_event(self)`** — decorators: —
  - touches: `voting.session`, `voting.vote`

### `hr.rfid.workcode` <a id='model-hr-rfid-workcode'></a>
Python class `HrRfidWorkcode` in `models/hr_rfid_workcode.py:6`.  Model.  Inherits: `hr.rfid.workcode`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `user_action` | Selection |  |  | ✓ |  |

### `onboarding.onboarding` <a id='model-onboarding-onboarding'></a>
Python class `OnboardingOnboarding` in `models/onboarding_onboarding.py:4`.  Model.  Inherits: `onboarding.onboarding`.

#### Notable methods

- **`action_close_panel_voting_setup(self)`** — decorators: `@api.model`
  - effects: `sudo`

### `onboarding.onboarding.step` <a id='model-onboarding-onboarding-step'></a>
Python class `OnboardingOnboardingStep` in `models/onboarding_onboarding_step.py:4`.  Model.  Inherits: `onboarding.onboarding.step`.

#### Notable methods

- **`action_open_step_voting_display(self)`** — decorators: `@api.model`
  - touches: `ir.actions.act_window`
- **`action_open_step_voting_participants(self)`** — decorators: `@api.model`
  - touches: `ir.actions.act_window`
- **`action_open_step_voting_items(self)`** — decorators: `@api.model`
  - touches: `ir.actions.act_window`
- **`action_open_step_voting_session(self)`** — decorators: `@api.model`
  - touches: `ir.actions.act_window`

### `voting.vote` <a id='model-voting-vote'></a>
Python class `Vote` in `models/vote.py:4`.  Model.  Description: *Voting Vote*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `voting_item_id` | Many2one → \`voting.item\` | Voting for | ✓ | ✓ | The question or motion this ballot answers. |
| `voting_session_id` | Many2one → \`voting.session\` | Voting Session | ✓ | ✓ | Session in which the ballot was cast. New ballots can only be created against an |
| `voter_id` | Many2one → \`res.partner\` | Voter | ✓ | ✓ | Participant who cast this ballot. Uniqueness is enforced — one ballot per voter  |
| `vote` | Selection |  | ✓ | ✓ | Voter's answer. |
| `vote_event_id` | Many2one → \`hr.rfid.event.user\` | Vote Event |  | ✓ | The RFID Granted event recorded when the voter tapped their card on the terminal |
| `vote_time` | Datetime | Vote Time |  | — | Exact moment the voter tapped their card (read from the linked RFID event). |

#### Notable methods

- **`create(self, vals_list)`** — decorators: `@api.model_create_multi`
  - calls `super() `create``

### `voting.display` <a id='model-voting-display'></a>
Python class `VotingDisplay` in `models/voting_display.py:8`.  Model.  Inherits: `mail.thread`.  Description: *Voting Display*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name of the voting Display | ✓ | ✓ | Internal name of the kiosk display (e.g. 'Main Hall Kiosk', 'Board Room Tablet') |
| `description` | Html | Announcements |  | ✓ | HTML content shown on the kiosk while no session is open. Use it for rules, open |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | Company that owns the display. Displays are isolated per company. |
| `voting_session_ids` | One2many → \`voting.session\` | Voting Display |  | ✓ | Sessions that have been hosted on this display. Used by the Sessions smart butto |
| `short_code` | Char | Short Code | ✓ | ✓ | Short 8-character public identifier that appears in the kiosk URL (\`/voting_dis |
| `access_token` | Char | Access Token | ✓ | ✓ | Internal UUID used by the bus to route real-time events to this display. Not sho |
| `display_url` | Char | Voting Display URL |  | — | Full public URL of the kiosk page. Open this on the device that voters interact  |
| `no_voting_background_color` | Char | No Voting Background Color |  | ✓ | Hex colour for the kiosk background when no session is active (default: teal). |
| `voting_background_color` | Char | Voting Background Color |  | ✓ | Hex colour for the kiosk background while a session is open (default: red). |
| `display_background_image` | Image | Background Image |  | ✓ | Optional image displayed behind the kiosk content. Falls back to the colour fiel |
| `voting_sessions_count` | Integer | Voting Sessions Count |  | — | Number of sessions ever hosted on this display. Updated automatically. |

#### Notable methods

- **`regenerate_display_key(self)`** — decorators: —
  - effects: `write`
- **`_compute_voting_sessions_count(self)`** — decorators: `@api.depends`
  - touches: `voting.session`
- **`_compute_display_url(self)`** — decorators: `@api.depends`
- **`action_open_display_view(self)`** — decorators: —
- **`action_view_sessions(self)`** — decorators: —

### `voting.item` <a id='model-voting-item'></a>
Python class `VotingItem` in `models/voting_item.py:4`.  Model.  Inherits: `mail.thread`, `mail.activity.mixin`.  Description: *Voting Item*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name of the voting Item | ✓ | ✓ | Title of the question or motion (e.g. 'Approve 2026 budget'). Shown on the kiosk |
| `short_description` | Text |  |  | ✓ | Short summary of the question shown beside the title on the kiosk. Keep it under |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | Company that owns the voting item. Items are isolated per company. |
| `document` | Html | Document |  | ✓ | Full text of the motion shown on the kiosk when the voter taps Read more. Use it |
| `voting_session_id` | One2many → \`voting.session\` | Voting Session |  | ✓ | Sessions that include this item. Read-only — managed from the session's Items li |
| `vote_ids` | One2many → \`voting.vote\` | Votes |  | ✓ | Ballots cast for this item across all sessions. Useful for historical analysis o |

### `voting.participants` <a id='model-voting-participants'></a>
Python class `VotingParticipants` in `models/voting_participants.py:4`.  Model.  Inherits: `mail.thread`.  Description: *Voting Participants*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name of the voting Group | ✓ | ✓ | Label for this participants list (e.g. 'Board of Directors', 'Shareholders Class |
| `description` | Text | Description of the voting Group |  | ✓ | Optional notes about who this group represents — useful as context when assignin |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | Company that owns the participants list. Participants are isolated per company. |
| `participant_ids` | Many2many → \`res.partner\` | Participants | ✓ | ✓ | Contacts allowed to vote. Each participant identifies themselves at the kiosk by |
| `terminal_ids` | Many2many → \`hr.rfid.door\` | Terminals | ✓ | ✓ | RFID readers participants will tap to identify themselves before casting a ballo |

### `voting.session` <a id='model-voting-session'></a>
Python class `VotingSession` in `models/voting_session.py:12`.  Model.  Inherits: `mail.thread`, `mail.activity.mixin`.  Description: *Voting Session*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name of the voting Session | ✓ | ✓ | Public title of the session shown on the kiosk header and in audit reports (e.g. |
| `description` | Text |  |  | ✓ | Optional long-form description of the session shown on the kiosk between voting  |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | Company that owns the session. Sessions are isolated per company; users only see |
| `planned_date` | Date | Planned Vote Date | ✓ | ✓ | Calendar date the session is planned for. Used by filters and the calendar view; |
| `start_datetime` | Datetime |  |  | ✓ | Timestamp the session was actually opened. Set automatically when an admin click |
| `end_datetime` | Datetime |  |  | ✓ | Timestamp the session was closed. Set automatically when an admin clicks Close S |
| `state` | Selection |  | ✓ | ✓ | Lifecycle of the session — Draft: not yet open, voters cannot cast ballots. Open |
| `new_session_id` | Many2one → \`voting.session\` | New Session |  | ✓ | If this session was re-voted, this is the replacement session that carries the n |
| `old_session_id` | Many2one → \`voting.session\` | Old Session |  | ✓ | If this session is itself a re-vote, this links back to the original session who |
| `participant_group_id` | Many2one → \`voting.participants\` | Participant Group | ✓ | ✓ | The participants list defining who can vote in this session. The same group can  |
| `item_ids` | Many2many → \`voting.item\` | Voting Items | ✓ | ✓ | One or more questions presented to voters in this session. Items are shown seque |
| `display_id` | Many2one → \`voting.display\` | Display | ✓ | ✓ | The kiosk display that hosts this session. Only one session at a time may be Ope |
| `voting_time` | Integer | Voting Time |  | ✓ | Time in seconds for voting |
| `vote_results_time` | Integer | Vote Results Time |  | ✓ | Time in seconds for showing the vote results |
| `vote_ids` | One2many → \`voting.vote\` | Votes |  | ✓ | Individual ballots cast in this session. Each row links a participant (or anonym |
| `vote_yes` | Integer | Yes |  | — | Live count of Yes ballots in this session. |
| `vote_no` | Integer | No |  | — | Live count of No ballots in this session. |
| `vote_abstain` | Integer | Abstain |  | — | Live count of Abstain ballots in this session. |
| `vote_total` | Integer | All Votes |  | — | Total number of ballots cast in this session (Yes + No + Abstain). |
| `final_vote` | Selection |  |  | — | Aggregate outcome computed from the running tally. Yes if Yes > No; No otherwise |

#### Notable methods

- **`action_vote_result_send(self)`** — decorators: —
  - Opens a wizard to compose an email, with relevant mail template loaded by default
  - effects: `with_context`
- **`_check_display_state(self)`** — decorators: `@api.constrains`
  - effects: `raise:ValidationError`
- **`_compute_votes(self)`** — decorators: `@api.depends`
- **`open_votes_action(self)`** — decorators: —
- **`button_open_voting_session(self)`** — decorators: —
  - effects: `write`
- **`button_close_voting_session(self)`** — decorators: —
  - effects: `write`
- **`notify_voting_session_state(self)`** — decorators: —
- **`button_re_voting_session(self)`** — decorators: —
  - effects: `write`
- **`write(self, vals)`** — decorators: —
  - calls `super() `write``
- **`create(self, vals_list)`** — decorators: `@api.model_create_multi`
  - calls `super() `create``


## Module Constants <a id='constants'></a>

No module-level UPPER_CASE constants are declared by this module.


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`VoteController.voting_main(self, short_code)`** (`@http.route`) — `controllers/voting.py:16`
  - effects: `sudo`
  - touches: `voting.display`
- **`VoteController.display_background_image(self, access_token)`** (`@http.route`) — `controllers/voting.py:23`
  - touches: `ir.binary`
- **`VoteController.get_existing_sessions(self, access_token)`** (`@http.route`) — `controllers/voting.py:31`
  - effects: `sudo`
  - touches: `voting.session`
- **`VoteController.session_close(self, access_token, session_id, state=None, **kwargs)`** (`@http.route`) — `controllers/voting.py:43`
  - effects: `message_post`
- **`TestVotingOnboarding.setUpClass(cls)`** (`@classmethod`) — `tests/test_onboarding.py:11`
  - calls `super()`
- **`TestVotingOnboarding.test_panel_has_four_steps_in_order(self)`** — `tests/test_onboarding.py:21`
- **`TestVotingOnboarding.test_all_step_actions_resolve_to_real_windows(self)`** — `tests/test_onboarding.py:29`
  - touches: `onboarding.onboarding.step`
- **`TestVotingOnboarding.test_each_step_completes_independently(self)`** — `tests/test_onboarding.py:36`
  - touches: `voting.display`, `voting.item`, `voting.participants`, `voting.session`
- **`TestVotingPublicControllers.setUpClass(cls)`** (`@classmethod`) — `tests/test_voting_controllers.py:16`
  - calls `super()`
  - touches: `voting.display`, `voting.participants`, `voting.session`
- **`TestVotingPublicControllers.test_voting_main_returns_kiosk_html(self)`** — `tests/test_voting_controllers.py:53`
- **`TestVotingPublicControllers.test_voting_main_unknown_short_code_returns_404(self)`** — `tests/test_voting_controllers.py:58`
- **`TestVotingPublicControllers.test_get_existing_sessions_returns_only_today(self)`** — `tests/test_voting_controllers.py:77`
- **`TestVotingPublicControllers.test_get_existing_sessions_invalid_token_returns_404(self)`** — `tests/test_voting_controllers.py:88`
- **`TestVotingPublicControllers.test_session_close_persists_state(self)`** — `tests/test_voting_controllers.py:102`
  - touches: `res.partner`, `voting.item`, `voting.vote`
- **`TestVotingPublicControllers.test_session_close_unknown_session_returns_404(self)`** — `tests/test_voting_controllers.py:126`

### Private helpers

- **`VoteController._fetch_sessions(self, display_id, access_token)`** — `controllers/voting.py:56`
  - Return the sudo-ed booking if it takes place in the room corresponding
- **`VoteController._fetch_display_from_access_token(self, access_token)`** — `controllers/voting.py:66`
  - Return the sudo-ed record of the display corresponding to the given
  - effects: `sudo`
  - touches: `voting.display`
- **`TestVotingPublicControllers._jsonrpc(self, url, params=None)`** — `tests/test_voting_controllers.py:64`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `vote_session_view_search` | `voting.session` | — |  | `views/vote_session_views.xml` |
| `vote_session_view_calendar` | `voting.session` | — |  | `views/vote_session_views.xml` |
| `vote_session_view_list` | `voting.session` | — |  | `views/vote_session_views.xml` |
| `vote_session_view_kanban` | `voting.session` | — |  | `views/vote_session_views.xml` |
| `vote_session_view_form` | `voting.session` | — |  | `views/vote_session_views.xml` |
| `voting_display_view_list` | `voting.display` | — |  | `views/voting_display_views.xml` |
| `voting_display_view_form` | `voting.display` | — |  | `views/voting_display_views.xml` |
| `voting_item_view_list` | `voting.item` | — |  | `views/voting_item_views.xml` |
| `voting_item_view_form` | `voting.item` | — |  | `views/voting_item_views.xml` |
| `voting_participants_view_list` | `voting.participants` | — |  | `views/voting_participants_views.xml` |
| `voting_participants_view_form` | `voting.participants` | — |  | `views/voting_participants_views.xml` |
| `voting_vote_view_search` | `voting.vote` | — |  | `views/voting_vote_views.xml` |
| `voting_vote_view_list` | `voting.vote` | — |  | `views/voting_vote_views.xml` |
| `voting_vote_view_form` | `voting.vote` | — |  | `views/voting_vote_views.xml` |


## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


**Groups defined**: `group_operator`, `group_manager`, `group_room_manager`


### Access rights (ir.model.access)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `hr_rfid_vertical_elections.access_voting_item` | `hr_rfid_vertical_elections.model_voting_item` | `hr_rfid_vertical_elections.group_manager` | ✓ | ✓ | ✓ | ✓ |

| `hr_rfid_vertical_elections.access_voting_participants` | `hr_rfid_vertical_elections.model_voting_participants` | `hr_rfid_vertical_elections.group_manager` | ✓ | ✓ | ✓ | ✓ |

| `hr_rfid_vertical_elections.access_voting_session` | `hr_rfid_vertical_elections.model_voting_session` | `hr_rfid_vertical_elections.group_manager` | ✓ | ✓ | ✓ | ✓ |

| `hr_rfid_vertical_elections.access_voting_vote` | `hr_rfid_vertical_elections.model_voting_vote` | `hr_rfid_vertical_elections.group_manager` | ✓ |  |  |  |

| `hr_rfid_vertical_elections.access_voting_display` | `hr_rfid_vertical_elections.model_voting_display` | `hr_rfid_vertical_elections.group_manager` | ✓ | ✓ | ✓ | ✓ |


### Record rules (ir.rule)

- **`room_room_comp_rule`** on `model_room_room` — perms=`R`, groups=`global`, domain=`[('company_id', 'in', company_ids)]`
- **`room_office_comp_rule`** on `model_room_office` — perms=`R`, groups=`global`, domain=`[('company_id', 'in', company_ids)]`


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Data records summary

- `onboarding.onboarding.step`: 4 record(s)
- `onboarding.onboarding`: 1 record(s)


## UI & Frontend <a id='assets'></a>

JavaScript, SCSS, OWL components and QWeb templates shipped by this module.


**OWL components**: `DisplayTime`, `DisplayView`, `SessionRemainingTime`, `SessionVoteResult`


**JS files** (5): `static/src/display/display_time.js`, `static/src/display/display_view/display_view.js`, `static/src/display/session_remaining_time.js`, `static/src/display/session_vote_result.js`, `static/src/display/useInterval.js`


**SCSS files** (3): `static/src/display/bootstrap_overridden.scss`, `static/src/display/main.scss`, `static/src/display/primary_variables.scss`


**QWeb templates** (1): `static/src/display/display_view/display_view.xml`



## Diagrams & Screenshots <a id='images'></a>
Visual assets shipped with the module. Captions generated by VLM; review before production.

<figure id='fig-static-description-icon-png'>

![Icon](static/description/icon.png)

<figcaption>[Placeholder caption] Image at `icon.png`. A vision-language model has not been configured yet. Replace this caption with a real description (VLM-generated or manual) to improve retrieval quality.</figcaption>
</figure>

> Tags: `icon`

<figure id='fig-static-description-icon-svg'>

![Icon](static/description/icon.svg)

<figcaption>[Placeholder caption] Image at `icon.svg`. A vision-language model has not been configured yet. Replace this caption with a real description (VLM-generated or manual) to improve retrieval quality.</figcaption>
</figure>

> Tags: `icon`


## FAQ & Troubleshooting <a id='faq'></a>
Candidate entries mined from code comments, git history and past Claude Code sessions. Review before publishing; `<!-- source: ... -->` markers should be removed after vetting.

### From `code_comments` (1)

#### TODO: Need separation between sessions with votes and without votes
<!-- source: code_comments ref: models/voting_session.py:239 occ: 1 conf: 0.50 -->

**TODO** in `models/voting_session.py:239`

> Need separation between sessions with votes and without votes

### From `gotchas` (12)

#### Gotcha: `@api.onchange` **НЕ** се вика при `create()` — само при UI промяна. З
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.70 -->

From **Модели и полета** in odoo19-gotchas.md:

> `@api.onchange` **НЕ** се вика при `create()` — само при UI промяна. За логика при create ползвай `@api.model_create_multi` или `_compute`

Matched tokens: `@api.model_create_multi, _compute, api.model_create_multi`

#### Gotcha: `_registry_readonly_enabled = False` (НЕ `readonly_enabled`) за `HttpC
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.70 -->

From **Тестове** in odoo19-gotchas.md:

> `_registry_readonly_enabled = False` (НЕ `readonly_enabled`) за `HttpCase` тестове с DB writes

Matched tokens: `_registry_readonly_enabled = false, readonly_enabled, httpcase`

#### Gotcha: **TransientModel + `target='current'` = dead link.** TransientModel за
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.70 -->

From **Wizards & TransientModel** in odoo19-gotchas.md:

> **TransientModel + `target='current'` = dead link.** TransientModel записи биват изтрити от autovacuum cron след минути до часове. Ако `action_window` връща `target='current'` с `res_id`, browser-ът bookmark-ва URL `/odoo/<model>/<id>` — следващ refresh/back-button → 404 "тотална грешка" / "запис не съществува". **Винаги** използвай `target='new'` (modal dialog) — modal-ите не променят URL-а, така че няма bookmarkable стара ID. Ако имаш Next/Back бутони (`type="object"`), pre-create record-а в `action_open_wizard()` за да съществува за compute_field-а, но дръж dialog-а modal. Производна на това: `_reopen()` helper-и за multistep wizard-и също трябва да са `target='new'`, не `'current'`.

Matched tokens: `type="object", 'current', res_id`

#### Gotcha: **`res.groups.category_id` премахнато** → `privilege_id` (M2O към `res
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.70 -->

From **Security & Constraints** in odoo19-gotchas.md:

> **`res.groups.category_id` премахнато** → `privilege_id` (M2O към `res.groups.privilege`, който има `category_id`). Pattern: създаваш `res.groups.privilege` с `category_id=ref('module_category_X')`, после групите имат `privilege_id=ref('res_groups_privilege_X')`.

Matched tokens: `res.groups.privilege, privilege_id, category_id`

#### Gotcha: SQL constraints (`models.Constraint`) предизвикват `IntegrityError`, н
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Модели и полета** in odoo19-gotchas.md:

> SQL constraints (`models.Constraint`) предизвикват `IntegrityError`, не `ValidationError`

Matched tokens: `models.constraint, validationerror`

#### Gotcha: **Statusbar `clickable="1"` заобикаля Python gating** — ако имаш `@api
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **Statusbar `clickable="1"` заобикаля Python gating** — ако имаш `@api.constrains` или action-based gating, премахни clickable за да форсираш потребителя през action бутон.

Matched tokens: `api.constrains, @api.constrains`

#### Gotcha: **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` ат
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` атрибут) се интерпретира от Odoo XML parser-а като `ir.model.data` external-ID lookup → `ValueError: External ID not found in the system: <module>.<name>`. Не може да бъде escape-нато с `%%`. Решение: преформулирай текста без `%(...)s` синтаксис (напр. `the placeholder <code>response_time</code>` вместо `<code>%(response_time)s</code>`).

Matched tokens: `<p>, help=`

#### Gotcha: `account.account` **НЯМА** `company_id` — ползвай уникални кодове (нап
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Модели и полета** in odoo19-gotchas.md:

> `account.account` **НЯМА** `company_id` — ползвай уникални кодове (напр. `411.NRA`)

Matched tokens: `company_id`

#### Gotcha: `size=N` на `fields.Char` е **UI hint**, не DB constraint — не разчита
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Модели и полета** in odoo19-gotchas.md:

> `size=N` на `fields.Char` е **UI hint**, не DB constraint — не разчитай на него за валидация

Matched tokens: `fields.char`

#### Gotcha: **Kanban templates: `<t t-name="card">` НЕ `<t t-name="kanban-box">`**
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **Kanban templates: `<t t-name="card">` НЕ `<t t-name="kanban-box">`** — v18→v19 преименуване. Стария път минава XML lint и install, но при отваряне в браузъра гърми с `OwlError: Missing 'card' template`. Структурата на content също е олекотена (без `oe_kanban_card` обвивка — директно полета + footer).

Matched tokens: `<t t-name="kanban-box">`

#### Gotcha: **Search view: `<group>` без атрибути** — `expand="0"` и `string="Grou
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **Search view: `<group>` без атрибути** — `expand="0"` и `string="Group By"` са премахнати. Стария път гърми с `RELAXNG_ERR_INVALIDATTR`.

Matched tokens: `<group>`

#### Gotcha: **`<button icon="...">` очаква **една** иконна класа без namespace pre
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **`<button icon="...">` очаква **една** иконна класа без namespace prefix** — `icon="oi-arrow-right"` или `icon="fa-refresh"`. Двусловната `icon="oi oi-arrow-right"` (widget-style) НЕ работи на button — render-ът не я разпознава и template-ът резолва към `<img class="undefined me-1" src="oi oi-arrow-right">` (литералното "undefined" в class, цялата стойност в src). Бутонът работи функционално, но иконата е счупена. Core pattern: `account/views/res_config_settings_views.xml:105` ползва `icon="oi-arrow-right"`. Само `<widget>` (напр. `documentation_link`) приема пълния class string `icon="oi oi-fw oi-arrow-right"`. **Защо не се хваща от тестове**: XML lint минава, install минава, tours не валидират иконно рендериране, /verify pробите не рендират HTML. Единствен начин за catch — визуална inspection или grep adversarial: `grep -rn 'icon="oi ' views/*.xml`.

Matched tokens: `icon="fa-refresh"`

### From `git_log` (4)

#### Fix: [FIX] hr_rfid_vertical_elections: fix two production controller bugs + H
<!-- source: git_log ref: c3bc7efe824368c0aee143318e0206e367afd371 occ: 1 conf: 0.60 -->

Commit `c3bc7efe82` (2026-05-03): [FIX] hr_rfid_vertical_elections: fix two production controller bugs + HttpCase

#### Fix: [FIX] hr_rfid_vertical_elections: v19 RPC, English source, cleanup, test
<!-- source: git_log ref: 12db09570bd07641f95289f90aaee118c484e5d6 occ: 1 conf: 0.60 -->

Commit `12db09570b` (2026-05-01): [FIX] hr_rfid_vertical_elections: v19 RPC, English source, cleanup, tests

#### Fix: [MIG] all: Migrate hardware routes to Odoo 19 Json2Dispatcher
<!-- source: git_log ref: 57aba8363e96203480d3792434639abc1b2bc33b occ: 1 conf: 0.60 -->

Commit `57aba8363e` (2026-03-19): [MIG] all: Migrate hardware routes to Odoo 19 Json2Dispatcher

#### Fix: fix license
<!-- source: git_log ref: 6e49a3ef0cee2364b143dcd71a33030362365dd1 occ: 1 conf: 0.60 -->

Commit `6e49a3ef0c` (2024-09-09): fix license


## Source provenance <a id='provenance'></a>

- Module path: `/home/lubo/PycharmProjects/odoo19/custom-addons/polimex/hr_rfid_vertical_elections`
- Source digest: `sha256:7d35422a10a83a49a29b86c886b6f82aa8f83f7094c61bf681be937896d052ac`
- Generated at: `2026-05-14T11:16:44+00:00`
- Generator: `polimex_module_knowledge` (see `~/.claude/lib/polimex_module_knowledge/`)

## The setup checklist (onboarding banner) <a id='onboarding-banner'></a>

The banner is NOT a view class of this module. It is attached by putting the
onboarding's `route_name` in the CONTEXT of the action:

```xml
<field name="context">{'onboarding_route_name': 'hr_rfid_vertical_elections_setup'}</field>
```

on ``vote_session_action` (Vote Session, kanban/calendar/list/form)` (`views/vote_session_views.xml`). That is the whole integration on this side.

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
`_prepare_rendering_values` auto-completes its four steps (a `voting.display`, a `voting.participants`, a `voting.item` and a `voting.session` exist) for the CURRENT company
before delegating to core, and `action_close_panel_voting_setup` is the close action named on the
onboarding record. Nothing here has to know how the banner is drawn.
