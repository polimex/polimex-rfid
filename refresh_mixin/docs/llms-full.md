---
id: refresh_mixin
title: Polimex Refresh Mixin
module: refresh_mixin
module_version: 19.0.1.3.2
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Refresh Mixin for Odoo models
last_updated: '2026-06-16'
source_digest: sha256:1db12fb4fa2768a9770c8e9cc5a5ccedf565d9b40da9018b73f5d5a04c992e2b
depends:
- web
- bus
- web_hierarchy
entities:
  primary: refresh.mixin
  related:
  - res.company
keywords:
- company
- mixin
- models
- odoo
- refresh
- res
license: AGPL-3
author: Polimex Team <software@polimex.co>
category: Technical
installable: true
application: false
auto_install: false
counts:
  models: 2
  views: 1
  access_rules: 0
  record_rules: 0
  crons: 0
  images: 2
images:
- path: static/description/icon.png
  sha256: sha256:2f52884526d5ae6e18c84c3279292e81be3903d07e6b77c8e985891fb393fcdf
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/description/icon.svg
  sha256: sha256:7c29af8a374327f49f53996bf2dc321b3bbb34e6cf751fe49db7612bacd53291
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# Polimex Refresh Mixin — `refresh_mixin` v19.0.1.3.2

Refresh Mixin for Odoo models

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview — module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `refresh_mixin`
- **Version**: `19.0.1.3.2`
- **Category**: Technical
- **License**: AGPL-3
- **Author**: Polimex Team <software@polimex.co>
- **Application**: no
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `web`, `bus`, `web_hierarchy`

### README (verbatim)

#### Refresh Mixin

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-18.0.1.0.0-green.svg)](https://apps.odoo.com)

Reusable mixin for adding auto-refresh functionality to Odoo views.

##### 🎯 Overview

Refresh Mixin is a technical module that provides a reusable JavaScript mixin for adding automatic refresh capabilities to any Odoo view. It handles refresh timing, error recovery, focus detection, and provides a consistent API for implementing real-time updates across different view types.

##### ✨ Key Features

###### Core Functionality
- **View Agnostic**: Works with List, Kanban, Form views
- **Configurable Intervals**: Set custom refresh rates
- **Smart Refresh**: Only updates when needed
- **Error Handling**: Automatic retry with backoff

###### Performance Features
- **Focus Detection**: Pause when window inactive
- **Batch Updates**: Efficient data fetching
- **Memory Management**: No memory leaks
- **Network Optimization**: Minimal data transfer

###### Developer Friendly
- **Simple API**: Easy to implement
- **Event System**: Hook into refresh cycle
- **Debug Support**: Built-in logging
- **TypeScript Ready**: Type definitions available

##### 📋 Requirements

- Odoo 18.0+
- Modern web browser
- JavaScript ES6 support

###### No Dependencies
```python
'depends': ['web']  # Only core web module needed
```

##### 🛠️ Installation

```bash
./odoo-bin -d your_database -i refresh_mixin
```

No configuration needed - it's a developer tool.

##### 📖 Usage

###### Basic Implementation

Add refresh to a list view:

```javascript
odoo.define('my_module.RefreshableListView', function (require) {
    'use strict';
    
    const ListController = require('web.ListController');
    const RefreshMixin = require('refresh_mixin.RefreshMixin');
    
    const RefreshableListController = ListController.extend(RefreshMixin, {
        init: function (parent, model, renderer, params) {
            this._super.apply(this, arguments);
            // Set refresh interval (milliseconds)
            this.refreshInterval = 5000; // 5 seconds
            this.refreshEnabled = true;
        },
        
        start: function () {
            this.startRefresh();
            return this._super.apply(this, arguments);
        },
        
        destroy: function () {
            this.stopRefresh();
            this._super.apply(this, arguments);
        },
    });
    
    return RefreshableListController;
});
```

###### Advanced Usage

```javascript
const MyController = Controller.extend(RefreshMixin, {
    init: function () {
        this._super.apply(this, arguments);
        
        // Configuration
        this.refreshInterval = 10000;
        this.refreshEnabled = true;
        this.refreshOnFocus = true;
        this.refreshBackoff = true;
        this.maxRefreshInterval = 60000;
    },
    
    // Custom refresh logic
    _onRefresh: function () {
        console.log('Refreshing data...');
        
        // Call parent refresh
        return this._super.apply(this, arguments).then(() => {
            // Post-refresh actions
            this._updateCounters();
            this._notifyUsers();
        });
    },
    
    // Conditional refresh
    _shouldRefresh: function () {
        // Only refresh if we have records
        return this.model.get(this.handle).count > 0;
    },
    
    // Handle refresh errors
    _onRefreshError: function (error) {
        console.error('Refresh failed:', error);
        // Optionally show user notification
        this.displayNotification({
            title: 'Refresh Error',
            message: 'Failed to update data',
            type: 'warning',
        });
    },
});
```

##### 🔌 API Reference

###### Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `refreshInterval` | Number | 30000 | Refresh interval in milliseconds |
| `refreshEnabled` | Boolean | false | Enable/disable refresh |
| `refreshOnFocus` | Boolean | true | Pause refresh when window loses focus |
| `refreshBackoff` | Boolean | true | Increase interval on errors |
| `maxRefreshInterval` | Number | 300000 | Maximum interval when backing off |

###### Methods

###### `startRefresh()`
Start the automatic refresh cycle.
```javascript
this.startRefresh();
```

###### `stopRefresh()`
Stop the automatic refresh cycle.
```javascript
this.stopRefresh();
```

###### `forceRefresh()`
Trigger an immediate refresh.
```javascript
this.forceRefresh().then(() => {
    console.log('Refresh completed');
});
```

###### `setRefreshInterval(interval)`
Change the refresh interval.
```javascript
this.setRefreshInterval(10000); // 10 seconds
```

###### `pauseRefresh()`
Temporarily pause refreshing.
```javascript
this.pauseRefresh();
```

###### `resumeRefresh()`
Resume a paused refresh cycle.
```javascript
this.resumeRefresh();
```

###### Events

The mixin triggers events you can listen to:

```javascript
// Listen for refresh events
this.on('refresh:start', this, this._onRefreshStart);
this.on('refresh:complete', this, this._onRefreshComplete);
this.on('refresh:error', this, this._onRefreshError);
```

##### 🎨 UI Integration

###### Add Refresh Controls

```javascript
renderButtons: function ($node) {
    this._super.apply(this, arguments);
    
    // Add refresh button
    this.$refreshButton = $('<button/>')
        .addClass('btn btn-secondary')
        .text('Refresh')
        .click(this.forceRefresh.bind(this));
    
    this.$buttons.append(this.$refreshButton);
    
    // Add interval selector
    this.$intervalSelect = $('<select/>')
        .addClass('custom-select ml-2')
        .append('<option value="5000">5 seconds</option>')
        .append('<option value="10000">10 seconds</option>')
        .append('<option value="30000">30 seconds</option>')
        .val(this.refreshInterval)
        .change((e) => this.setRefreshInterval(e.target.value));
    
    this.$buttons.append(this.$intervalSelect);
},
```

###### Visual Indicators

```javascript
_onRefreshStart: function () {
    // Show loading indicator
    this.$('.o_list_view').addClass('o_refreshing');
},

_onRefreshComplete: function () {
    // Hide loading indicator
    this.$('.o_list_view').removeClass('o_refreshing');
    
    // Flash updated rows
    this.$('.o_data_row[data-updated="true"]')
        .addClass('o_refresh_highlight')
        .delay(1000)
        .queue(function () {
            $(this).removeClass('o_refresh_highlight').dequeue();
        });
},
```

##### ⚙️ Advanced Features

###### Intelligent Refresh

```javascript
// Only refresh if data has changed
_onRefresh: function () {
    return this.model.checkForUpdates(this.handle).then((hasUpdates) => {
        if (hasUpdates) {
            return this._super.apply(this, arguments);
        }
        console.log('No updates, skipping refresh');
    });
},
```

###### Batch Operations

```javascript
// Refresh multiple views together
const RefreshCoordinator = Class.extend({
    init: function () {
        this.controllers = [];
    },
    
    register: function (controller) {
        this.controllers.push(controller);
    },
    
    refreshAll: function () {
        return Promise.all(
            this.controllers.map(c => c.forceRefresh())
        );
    },
});
```

###### Performance Monitoring

```javascript
_onRefresh: function () {
    const startTime = performance.now();
    
    return this._super.apply(this, arguments).then(() => {
        const duration = performance.now() - startTime;
        console.log(`Refresh completed in ${duration}ms`);
        
        // Adjust interval based on performance
        if (duration > 1000 && this.refreshInterval < 30000) {
            this.setRefreshInterval(this.refreshInterval * 2);
        }
    });
},
```

##### 🐛 Troubleshooting

###### Common Issues

1. **Refresh not starting**
   ```javascript
   // Check these settings
   console.log('Enabled:', this.refreshEnabled);
   console.log('Interval:', this.refreshInterval);
   console.log('Timer ID:', this._refreshTimerId);
   ```

2. **Memory leaks**
   ```javascript
   // Always clean up in destroy
   destroy: function () {
       this.stopRefresh();
       this._super.apply(this, arguments);
   }
   ```

3. **Too frequent refreshes**
   ```javascript
   // Implement throttling
   _onRefresh: _.throttle(function () {
       return this._super.apply(this, arguments);
   }, 5000),
   ```

###### Debug Mode

Enable debug logging:
```javascript
// In your controller
init: function () {
    this._super.apply(this, arguments);
    this.refreshDebug = true; // Enable debug logs
}
```

##### 📊 Performance Best Practices

1. **Choose Appropriate Intervals**
   - High-frequency data: 5-10 seconds
   - Normal updates: 30-60 seconds  
   - Low-priority data: 2-5 minutes

2. **Optimize Data Fetching**
   - Only request needed fields
   - Use incremental updates
   - Implement server-side caching

3. **Handle Edge Cases**
   - Network disconnections
   - Session timeouts
   - Database locks

##### 🤝 Contributing

We welcome contributions:
1. Fork the repository
2. Add new features
3. Ensure backward compatibility
4. Submit pull request

##### 📄 License

Licensed under AGPL-3.0. See [LICENSE](../LICENSE) for details.

##### 👥 Credits

###### Authors
- Polimex Dev Team

###### Maintainer
- [Polimex](https://polimex.co)

##### 🌐 Links

- [Documentation](https://polimex.co/docs/refresh-mixin)
- [Examples](https://github.com/polimex/odoo-apps/tree/18.0/refresh_mixin/examples)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/refresh_mixin/)

---

For more information, visit [polimex.co](https://polimex.co)


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i refresh_mixin --stop-after-init
```


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `refresh.mixin` <a id='model-refresh-mixin'></a>
Python class `RefreshMixin` in `models/refresh_mixin.py:6`.  AbstractModel.  Description: *Model Refresh Mixin*.

> A mixin for models that need to refresh dashboard views via bus notifications.

#### Notable methods

- **`get_company_id(self)`** — decorators: —
  - Get company_id for the record(s). Returns first company if multiple records.
- **`send_notice(self, operation)`** — decorators: —
  - Send bus notification for dashboard refresh.
  - effects: `log_debug`, `log_warn`
  - touches: `bus.bus`
- **`write(self, vals)`** — decorators: —
  - calls `super() `write``
- **`create(self, vals_list)`** — decorators: `@api.model_create_multi`
  - calls `super() `create``

### `res.company` <a id='model-res-company'></a>
Python class `Company` in `models/res_company.py:4`.  Model.  Inherits: `res.company`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `realtime_refresh` | Boolean | Real-time View Refresh |  | ✓ | Enable automatic refresh of views when data changes.  • When enabled: Views auto |


## Module Constants <a id='constants'></a>

No module-level UPPER_CASE constants are declared by this module.


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`TestRefreshMixin.test_send_notice_emits_record_changed_for_write(self)`** — `tests/test_refresh_mixin.py:38`
- **`TestRefreshMixin.test_send_notice_emits_record_created_for_create(self)`** — `tests/test_refresh_mixin.py:50`
- **`TestRefreshMixin.test_send_notice_skipped_when_realtime_refresh_disabled(self)`** — `tests/test_refresh_mixin.py:59`
- **`TestRefreshMixin.test_send_notice_skipped_when_no_company_field(self)`** — `tests/test_refresh_mixin.py:65`
- **`TestRefreshMixin.test_unresolvable_company_does_not_warn(self)`** — `tests/test_refresh_mixin.py:71`
- **`TestRefreshMixin.test_extra_payload_is_merged(self)`** — `tests/test_refresh_mixin.py:82`

### Private helpers

- **`TestRefreshMixin._patch_bus(self)`** — `tests/test_refresh_mixin.py:18`
  - touches: `bus.bus`
- **`TestRefreshMixin._make_stub(self, *, has_company=True, realtime_refresh=True, ids=(1, 2), extra_payload=None)`** — `tests/test_refresh_mixin.py:22`
  - touches: `refresh.mixin`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `view_company_form_realtime_refresh` | `res.company` | — | base.view_company_form | `views/res_company_views.xml` |

#### Sample XPath operations

- In `view_company_form_realtime_refresh`:
  - `//group[@name='social_media'] [before]`



## Security <a id='security'></a>

This module does not declare any access rules, record rules or groups of its own. It relies entirely on permissions inherited from its dependencies.


## Data & Automation <a id='data'></a>

No XML data records or cron jobs are declared by this module.


## UI & Frontend <a id='assets'></a>

JavaScript, SCSS, OWL components and QWeb templates shipped by this module.


**JS files** (4): `static/src/js/hierarchy_refresh_view.js`, `static/src/js/kanban_refresh_view.js`, `static/src/js/list_refresh_view.js`, `static/src/js/use_bus_refresh.js`



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

### From `gotchas` (6)

#### Gotcha: `@api.onchange` **НЕ** се вика при `create()` — само при UI промяна. З
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Модели и полета** in odoo19-gotchas.md:

> `@api.onchange` **НЕ** се вика при `create()` — само при UI промяна. За логика при create ползвай `@api.model_create_multi` или `_compute`

Matched tokens: `@api.model_create_multi, api.model_create_multi`

#### Gotcha: `account.account` **НЯМА** `company_id` — ползвай уникални кодове (нап
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Модели и полета** in odoo19-gotchas.md:

> `account.account` **НЯМА** `company_id` — ползвай уникални кодове (напр. `411.NRA`)

Matched tokens: `company_id`

#### Gotcha: **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` ат
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` атрибут) се интерпретира от Odoo XML parser-а като `ir.model.data` external-ID lookup → `ValueError: External ID not found in the system: <module>.<name>`. Не може да бъде escape-нато с `%%`. Решение: преформулирай текста без `%(...)s` синтаксис (напр. `the placeholder <code>response_time</code>` вместо `<code>%(response_time)s</code>`).

Matched tokens: `help=`

#### Gotcha: **`message_post(body=...)` / `_message_log` / `mail.activity` третират
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Mail / Templates** in odoo19-gotchas.md:

> **`message_post(body=...)` / `_message_log` / `mail.activity` третират plain `str` като ТЕКСТ и го HTML-escape-ват — HTML в chatter иска `markupsafe.Markup`.** В Odoo 17+ ако подадеш `self.env._("... <b>%s</b> ...", val)` (връща plain `str`), `<b>` се escape-ва → потребителят вижда буквално `<b>resolve</b>` (в raw body: `&lt;b&gt;`). Динамичните стойности ТРЯБВА да се escape-ват (XSS защита), затова canonical pattern е `Markup(self.env._("... <b>%(x)s</b> ...")) % {"x": val}` — `Markup.__mod__` escape-ва само substituted-ите стойности, литералните тагове остават HTML. За чист plain-text note plain `str` е правилен (и по-безопасен — не пъхай HTML където не трябва). Core: `Markup("<b>%s</b>") % name` навсякъде в `mail/`. **Как се хваща**: rendирай note-а и assert `'<b>' in body and '&lt;b&gt;' not in body`; grep adversarial: `grep -rn 'message_post(' models/ | xargs grep -l '<b>\|<br\|<p>'` после провери за `Markup`.

Matched tokens: `str`

#### Gotcha: **Маркер/HTML-коментар сложен в `mail.mail.body_html` на CREATE-time с
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Mail / Templates** in odoo19-gotchas.md:

> **Маркер/HTML-коментар сложен в `mail.mail.body_html` на CREATE-time се мангълва от `_prepare_outgoing_body`→`_replace_local_links` (lxml re-serialise) на SEND-time.** `html_sanitize` (на store) ГО ЗАПАЗВА, но core `mail.mail._prepare_outgoing_body()` вика `mail.render.mixin._replace_local_links(body_html)`, който парсва+пресериализира HTML-а през lxml и чупи `<!--[...]-->` comment-а (маха отварящия `<!--`, оставя `]--&gt;`). Затова маркерът ТРЯБВА да се embed-ва в override на `_prepare_outgoing_body` **СЛЕД** `super()` (post-`_replace_local_links`), НЕ в `body_html`. За thread-less mail (без model/res_id — за да не цапа клиентския chatter с празно `email_outgoing` "message removed" phantom; `mail.mail` `_inherits` mail.message → model/res_id са на делегата → показва се в chatter) идентифицирай записа през друг канал (напр. `mail.mail.headers` sentinel, парсва се с `ast.literal_eval`) и embed-вай post-super. **Как се хваща**: assert `parse_metadata_xml(mail._prepare_outgoing_body())`, НЕ само `parse_metadata_xml(mail.body_html)` — body_html минава sanitize, но `_prepare_outgoing_body` лови lxml мангъла.

Matched tokens: `super()`

#### Gotcha: **Dotted domain `('a.b', '=', False)` НЕ матчва записи със счупена вер
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **ORM / Domains** in odoo19-gotchas.md:

> **Dotted domain `('a.b', '=', False)` НЕ матчва записи със счупена верига (`a = NULL`).** В v19 всяка dotted кондиция се декомпозира до `any` оператора (`odoo/orm/domains.py:937-941`) = EXISTS subquery — никога не матчва NULL междинен M2O. Доказано емпирично (hr_rfid, юни 2026): `['|', ('controller_id.webstack_id.company_id','=',False), ...]` в ir.rule НЕ направи controller-less събития видими. За всеки ОПЦИОНАЛЕН линк по веригата трябва изричен клон `('a','=',False)`; required линковете не могат да се счупят → без клон. ВИНАГИ тествай broken-chain записа отделно от terminal-NULL записа — вторият тест минава, докато първият още е скрит.

Matched tokens: `any`

### From `git_log` (3)

#### Fix: [FIX] drop test-framework import from module __init__ (A1)
<!-- source: git_log ref: d3925400454543d7999e8b92bce72f95f1a84e03 occ: 1 conf: 0.60 -->

Commit `d392540045` (2026-06-01): [FIX] drop test-framework import from module __init__ (A1)

#### Fix: [REF] refresh_mixin: shared useBusRefresh hook + race-condition fix
<!-- source: git_log ref: ff393adb84bc302d6af4e3147d9cfc1d48d0c545 occ: 1 conf: 0.60 -->

Commit `ff393adb84` (2026-05-01): [REF] refresh_mixin: shared useBusRefresh hook + race-condition fix

#### Fix: [FIX] refresh_mixin: Add missing res_company model and views
<!-- source: git_log ref: b44350f7776500c900617b01762f347bda819fd5 occ: 1 conf: 0.60 -->

Commit `b44350f777` (2025-12-19): [FIX] refresh_mixin: Add missing res_company model and views


## Source provenance <a id='provenance'></a>

- Module path: `/home/lubo/PycharmProjects/odoo19/custom-addons/polimex/refresh_mixin`
- Source digest: `sha256:1db12fb4fa2768a9770c8e9cc5a5ccedf565d9b40da9018b73f5d5a04c992e2b`
- Generated at: `2026-06-16T16:24:42+00:00`
- Generator: `polimex_module_knowledge` (see `~/.claude/lib/polimex_module_knowledge/`)
