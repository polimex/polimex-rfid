---
id: hr_rfid_refresh_views
title: RFID Refresh Views
module: hr_rfid_refresh_views
module_version: 19.0.1.3.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: "\n        Refresh RFID views\n    "
last_updated: '2026-11-23'
source_digest: sha256:d8e74438744f587014fefb20769e61188ed745144698fe2cbed3c01ef5608249
depends:
- hr_rfid
- refresh_mixin
entities:
  primary: hr.rfid.command
  related:
  - hr.rfid.ctrl
  - hr.rfid.ctrl.alarm
  - hr.rfid.ctrl.alarm.group
  - hr.rfid.door
  - hr.rfid.event
  - hr.rfid.webstack
keywords:
- alarm
- command
- ctrl
- door
- group
- refresh
- rfid
- views
license: AGPL-3
author: Polimex Team <software@polimex.co>
category: Administration
installable: true
application: false
auto_install: true
counts:
  models: 7
  views: 13
  access_rules: 0
  record_rules: 0
  crons: 0
  images: 2
images:
- path: static/description/icon.png
  sha256: sha256:efcbd91dbdb69b1409d388069b9959f7cda0ddb456485dcc99c2475020ebad50
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/description/icon.svg
  sha256: sha256:bd92825503d9c62f610afac8ae8f3c6458a9f299d6141b88a5a37d6c74537e71
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# RFID Refresh Views - `hr_rfid_refresh_views` v19.0.1.3.0


        Refresh RFID views
    

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview - module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_rfid_refresh_views`
- **Version**: `19.0.1.3.0`
- **Category**: Administration
- **License**: AGPL-3
- **Author**: Polimex Team <software@polimex.co>
- **Application**: no
- **Auto-install**: yes
- **Installable**: yes
- **Depends on**: `hr_rfid`, `refresh_mixin`

### README (verbatim)

#### RFID Refresh Views

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-18.0.1.0.0-green.svg)](https://apps.odoo.com)

Auto-refresh functionality for real-time RFID monitoring views.

##### 🎯 Overview

RFID Refresh Views adds automatic refresh capabilities to RFID-related views in Odoo, enabling real-time monitoring of access events, door statuses, and system alerts without manual page reloads. Essential for security monitoring and control room operations.

##### ✨ Key Features

###### Auto-Refresh Views
- **Event Lists**: Live access event updates
- **Door Status**: Real-time door state monitoring
- **Controller Status**: Online/offline indicators
- **Alarm Monitoring**: Instant alarm notifications

###### Configurable Intervals
- **Per-View Settings**: Different refresh rates
- **User Preferences**: Personal refresh settings
- **Performance Modes**: High/low frequency options
- **Pause/Resume**: Manual control available

###### Smart Refresh
- **Change Detection**: Refresh only on changes
- **Batch Updates**: Efficient data loading
- **Focus Aware**: Pause when window inactive
- **Error Recovery**: Automatic reconnection

##### 📋 Requirements

- Odoo 18.0+
- hr_rfid module
- refresh_mixin module
- Modern web browser with JavaScript

###### Dependencies
```python
'depends': ['hr_rfid', 'refresh_mixin']
```

##### 🛠️ Installation

1. Install dependencies first

2. Install the module:
```bash
./odoo-bin -d your_database -i hr_rfid_refresh_views
```

3. Refresh browser to load new features

##### 🔧 Configuration

###### Global Settings

Configure in Settings → Technical → System Parameters:
```python
#### Refresh intervals (seconds)
hr_rfid_refresh_views.event_interval = 5
hr_rfid_refresh_views.door_interval = 10
hr_rfid_refresh_views.alarm_interval = 3
hr_rfid_refresh_views.controller_interval = 30
```

###### Per-View Configuration

1. **Open View**: Navigate to desired view
2. **Settings Icon**: Click refresh settings
3. **Configure**:
   - Enable/disable auto-refresh
   - Set refresh interval
   - Choose refresh mode

###### User Preferences

Users can override defaults:
- My Preferences → RFID Monitoring
- Set personal refresh rates
- Enable/disable for specific views

##### 📖 Usage

###### Enabled Views

Auto-refresh is available for:

1. **Event Monitoring**
   - User Events (real-time)
   - System Events (30-second default)
   - Event dashboard

2. **Door Management**
   - Door list view
   - Door kanban cards
   - Emergency status

3. **Controller Monitoring**
   - Webstack status
   - Controller list
   - Network topology

4. **Alarm Center**
   - Active alarms
   - Alarm history
   - Alarm groups

###### Control Options

###### Manual Controls
- **Pause Button**: Temporarily stop refresh
- **Resume Button**: Restart auto-refresh
- **Refresh Now**: Force immediate update
- **Settings**: Adjust interval on-the-fly

###### Automatic Behaviors
- Pauses when editing records
- Resumes after save/cancel
- Stops on connection errors
- Restarts when connection restored

##### 🎨 Visual Indicators

###### Status Icons
- 🟢 **Green**: Auto-refresh active
- 🟡 **Yellow**: Refresh paused
- 🔴 **Red**: Connection error
- ⚪ **Gray**: Refresh disabled

###### Update Animations
- Smooth fade transitions
- Row highlighting for changes
- Count badges for new items
- Progress bar for next refresh

##### 🔌 Technical Details

###### JavaScript Implementation

```javascript
// Refresh mixin usage
odoo.define('hr_rfid_refresh_views.EventListView', function (require) {
    var ListController = require('web.ListController');
    var RefreshMixin = require('refresh_mixin.RefreshMixin');
    
    var EventListController = ListController.extend(RefreshMixin, {
        init: function () {
            this._super.apply(this, arguments);
            this.refreshInterval = 5000; // 5 seconds
        },
        
        willStart: function () {
            this.startRefresh();
            return this._super.apply(this, arguments);
        },
    });
});
```

###### Performance Optimization

```python
#### Efficient data fetching
class HrRfidEvent(models.Model):
    _inherit = 'hr.rfid.event'
    
    @api.model
    def get_refresh_data(self, last_update):
        # Return only changed records
        domain = [('write_date', '>', last_update)]
        return self.search_read(domain, ['id', 'name', 'door_id'])
```

##### ⚙️ Advanced Features

###### Custom Refresh Logic

```javascript
// Add custom refresh behavior
_onRefresh: function () {
    // Custom pre-refresh logic
    if (this._checkSpecialCondition()) {
        this.refreshInterval = 1000; // Speed up
    }
    
    return this._super.apply(this, arguments).then(function () {
        // Post-refresh actions
        this._updateDashboard();
    }.bind(this));
}
```

###### Conditional Refresh

```python
#### Server-side refresh hints
@api.model
def should_refresh(self, view_type, last_refresh):
    if view_type == 'alarm':
        # Check for active alarms
        return self.env['hr.rfid.ctrl.alarm'].search_count([
            ('state', '=', 'active'),
            ('create_date', '>', last_refresh)
        ]) > 0
    return False
```

##### 🐛 Troubleshooting

###### Common Issues

1. **Views not refreshing**
   - Check JavaScript console
   - Verify refresh_mixin installed
   - Clear browser cache

2. **Performance problems**
   - Increase refresh interval
   - Check server load
   - Optimize view filters

3. **Flickering updates**
   - Enable smooth transitions
   - Adjust animation speed
   - Check network latency

###### Debug Mode

Enable debug logging:
```javascript
// In browser console
odoo.debug = true;
localStorage.setItem('debug', 'assets,refresh');
```

##### 📊 Performance Impact

###### Resource Usage
- Minimal CPU impact
- Network: ~1KB per refresh
- Memory: No accumulation
- Battery: Optimized for mobile

###### Best Practices
- Use appropriate intervals
- Disable for static data
- Pause when not viewing
- Filter unnecessary fields

##### 🤝 Contributing

Contributions welcome:
1. Fork repository
2. Add new view support
3. Test performance impact
4. Submit pull request

##### 📄 License

Licensed under AGPL-3.0. See [LICENSE](../LICENSE) for details.

##### 👥 Credits

###### Authors
- Polimex Dev Team

###### Maintainer
- [Polimex](https://polimex.co)

##### 🌐 Links

- [Documentation](https://polimex.co/docs/rfid-refresh)
- [Performance Guide](https://polimex.co/docs/rfid-refresh-performance)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/hr_rfid_refresh_views/)

---

For more information, visit [polimex.co](https://polimex.co)


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i hr_rfid_refresh_views --stop-after-init
```

> **Auto-install**: Odoo installs it by itself only in an operation that installs one of `hr_rfid`, `refresh_mixin` while the rest of them are installed or installed in the same operation. A database that already has all of them does not get it by itself - not on an upgrade (`-u`), not on Update Apps List: install it once from Apps or with the command above.


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `hr.rfid.command` <a id='model-hr-rfid-command'></a>
Python class `HrRfidCommands` in `models/hr_rfid_command.py:5`.  Model.  Inherits: `hr.rfid.command`, `refresh.mixin`.  Description: *Command to controller*.

#### Notable methods

- **`get_company_id(self)`** - decorators: -
- **`get_company_ids(self)`** - decorators: -

### `hr.rfid.ctrl` <a id='model-hr-rfid-ctrl'></a>
Python class `HrRfidController` in `models/hr_rfid_ctrl.py:5`.  Model.  Inherits: `hr.rfid.ctrl`, `refresh.mixin`.  Description: *Controller*.

#### Notable methods

- **`get_company_id(self)`** - decorators: -
- **`get_company_ids(self)`** - decorators: -

### `hr.rfid.ctrl.alarm` <a id='model-hr-rfid-ctrl-alarm'></a>
Python class `HrRfidCtrlAlarm` in `models/hr_rfid_ctrl_alarm.py:6`.  Model.  Inherits: `hr.rfid.ctrl.alarm`, `refresh.mixin`.

#### Notable methods

- **`get_company_id(self)`** - decorators: -
- **`get_company_ids(self)`** - decorators: -

### `hr.rfid.ctrl.alarm.group` <a id='model-hr-rfid-ctrl-alarm-group'></a>
Python class `HrRfidCtrlAlarmGroup` in `models/hr_rfid_ctrl_alarm_group.py:5`.  Model.  Inherits: `hr.rfid.ctrl.alarm.group`, `refresh.mixin`.  Description: *Alarm system groups*.

### `hr.rfid.door` <a id='model-hr-rfid-door'></a>
Python class `HrRfidDoor` in `models/hr_rfid_door.py:6`.  Model.  Inherits: `hr.rfid.door`, `refresh.mixin`.  Description: *Door*.

#### Notable methods

- **`get_company_id(self)`** - decorators: -
- **`get_company_ids(self)`** - decorators: -

### `hr.rfid.event` <a id='model-hr-rfid-event'></a>
Python class `HRRFIDEvent` in `models/hr_rfid_event.py:5`.  AbstractModel.  Inherits: `hr.rfid.event`, `refresh.mixin`.  Description: *Helper for RFID Events*.

#### Notable methods

- **`get_company_id(self)`** - decorators: -
- **`get_company_ids(self)`** - decorators: -
  - touches: `hr.rfid.webstack`, `res.company`

### `hr.rfid.webstack` <a id='model-hr-rfid-webstack'></a>
Python class `HrRfidWebstack` in `models/hr_rfid_webstack.py:5`.  Model.  Inherits: `hr.rfid.webstack`, `refresh.mixin`.  Description: *Module*.

#### Notable methods

- **`get_company_ids(self)`** - decorators: -


## Module Constants <a id='constants'></a>

No module-level UPPER_CASE constants are declared by this module.


## Module Helpers & Hooks <a id='helpers'></a>

No module-level helper functions or install hooks are declared.


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `hr_rfid_command_view_tree_refresh` | `hr.rfid.command` | - | hr_rfid.hr_rfid_command_view_list | `views/hr_rfid_command.xml` |
| `hr_rfid_controller_view_tree_refresh` | `hr.rfid.ctrl` | - | hr_rfid.hr_rfid_controller_view_list | `views/hr_rfid_ctrl.xml` |
| `hr_rfid_controller_view_kanban_refresh` | `hr.rfid.ctrl` | - | hr_rfid.hr_rfid_controller_view_kanban | `views/hr_rfid_ctrl.xml` |
| `hr_rfid_ctrl_alarm_tree_view_refresh` | `hr.rfid.ctrl.alarm` | - | hr_rfid.hr_rfid_ctrl_alarm_list_view | `views/hr_rfid_ctrl_alarm.xml` |
| `hr_rfid_ctrl_alarm_view_kanban_refresh` | `hr.rfid.ctrl.alarm` | - | hr_rfid.hr_rfid_ctrl_alarm_view_kanban | `views/hr_rfid_ctrl_alarm.xml` |
| `hr_rfid_ctrl_alarm_group_hierarchy_view_refresh` | `hr.rfid.ctrl.alarm.group` | - | hr_rfid.hr_rfid_ctrl_alarm_group_hierarchy_view | `views/hr_rfid_ctrl_alarm_group.xml` |
| `hr_rfid_door_view_kanban_refresh` | `hr.rfid.door` | - | hr_rfid.hr_rfid_door_view_kanban | `views/hr_rfid_door.xml` |
| `hr_rfid_sys_ev_view_tree_refresh` | `hr.rfid.event.system` | - | hr_rfid.hr_rfid_sys_ev_view_list | `views/hr_rfid_event_system.xml` |
| `hr_rfid_user_ev_view_tree_refresh` | `hr.rfid.event.user` | - | hr_rfid.hr_rfid_user_ev_view_list | `views/hr_rfid_event_user.xml` |
| `hr_rfid_webstack_view_tree_refresh` | `hr.rfid.webstack` | - | hr_rfid.hr_rfid_webstack_view_list | `views/hr_rfid_webstack.xml` |
| `hr_rfid_webstack_view_kanban_refresh` | `hr.rfid.webstack` | - | hr_rfid.hr_rfid_webstack_view_kanban | `views/hr_rfid_webstack.xml` |
| `view_company_form_hide_realtime_refresh` | `res.company` | - | refresh_mixin.view_company_form_realtime_refresh | `views/res_company.xml` |
| `rfid_form_inherit_res_company_refresh` | `res.company` | - | hr_rfid.rfid_form_inherit_res_company | `views/res_company.xml` |

#### Sample XPath operations

- In `hr_rfid_command_view_tree_refresh`:
  - `//list [attributes]`

- In `hr_rfid_controller_view_tree_refresh`:
  - `//list [attributes]`

- In `hr_rfid_controller_view_kanban_refresh`:
  - `//kanban [attributes]`

- In `hr_rfid_ctrl_alarm_tree_view_refresh`:
  - `//list [attributes]`

- In `hr_rfid_ctrl_alarm_view_kanban_refresh`:
  - `//kanban [attributes]`



## Security <a id='security'></a>

This module does not declare any access rules, record rules or groups of its own. It relies entirely on permissions inherited from its dependencies.


## Data & Automation <a id='data'></a>

No XML data records or cron jobs are declared by this module.


## UI & Frontend <a id='assets'></a>

This module ships no frontend assets (no JavaScript, SCSS, OWL components or QWeb templates).


## Diagrams & Screenshots <a id='images'></a>
Visual assets shipped with the module.

<figure id='fig-static-description-icon-png'>

![Icon](static/description/icon.png)

<figcaption>Icon</figcaption>
</figure>

> Tags: `icon`

<figure id='fig-static-description-icon-svg'>

![Icon](static/description/icon.svg)

<figcaption>Icon</figcaption>
</figure>

> Tags: `icon`


## FAQ & Troubleshooting <a id='faq'></a>
Entries derived from the module's own code comments and bug-fix commit history.

### From `git_log` (2)

#### Fix: [FIX] refresh layer: camera events never refreshed the realtime ...

Commit `139e5c19da` (2026-06-17): [FIX] refresh layer: camera events never refreshed the realtime dashboard

#### Fix: [FIX] drop test-framework import from module __init__ (A1)

Commit `d392540045` (2026-06-01): [FIX] drop test-framework import from module __init__ (A1)


## Source provenance <a id='provenance'></a>

- Module: `hr_rfid_refresh_views`
- Source digest: `sha256:d8e74438744f587014fefb20769e61188ed745144698fe2cbed3c01ef5608249`
- Generated at: `2026-11-23T10:04:54+00:00`
- Generator: `polimex_module_knowledge`
