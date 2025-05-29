# Refresh Mixin

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-18.0.1.0.0-green.svg)](https://apps.odoo.com)

Reusable mixin for adding auto-refresh functionality to Odoo views.

## 🎯 Overview

Refresh Mixin is a technical module that provides a reusable JavaScript mixin for adding automatic refresh capabilities to any Odoo view. It handles refresh timing, error recovery, focus detection, and provides a consistent API for implementing real-time updates across different view types.

## ✨ Key Features

### Core Functionality
- **View Agnostic**: Works with List, Kanban, Form views
- **Configurable Intervals**: Set custom refresh rates
- **Smart Refresh**: Only updates when needed
- **Error Handling**: Automatic retry with backoff

### Performance Features
- **Focus Detection**: Pause when window inactive
- **Batch Updates**: Efficient data fetching
- **Memory Management**: No memory leaks
- **Network Optimization**: Minimal data transfer

### Developer Friendly
- **Simple API**: Easy to implement
- **Event System**: Hook into refresh cycle
- **Debug Support**: Built-in logging
- **TypeScript Ready**: Type definitions available

## 📋 Requirements

- Odoo 18.0+
- Modern web browser
- JavaScript ES6 support

### No Dependencies
```python
'depends': ['web']  # Only core web module needed
```

## 🛠️ Installation

```bash
./odoo-bin -d your_database -i refresh_mixin
```

No configuration needed - it's a developer tool.

## 📖 Usage

### Basic Implementation

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

### Advanced Usage

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

## 🔌 API Reference

### Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `refreshInterval` | Number | 30000 | Refresh interval in milliseconds |
| `refreshEnabled` | Boolean | false | Enable/disable refresh |
| `refreshOnFocus` | Boolean | true | Pause refresh when window loses focus |
| `refreshBackoff` | Boolean | true | Increase interval on errors |
| `maxRefreshInterval` | Number | 300000 | Maximum interval when backing off |

### Methods

#### `startRefresh()`
Start the automatic refresh cycle.
```javascript
this.startRefresh();
```

#### `stopRefresh()`
Stop the automatic refresh cycle.
```javascript
this.stopRefresh();
```

#### `forceRefresh()`
Trigger an immediate refresh.
```javascript
this.forceRefresh().then(() => {
    console.log('Refresh completed');
});
```

#### `setRefreshInterval(interval)`
Change the refresh interval.
```javascript
this.setRefreshInterval(10000); // 10 seconds
```

#### `pauseRefresh()`
Temporarily pause refreshing.
```javascript
this.pauseRefresh();
```

#### `resumeRefresh()`
Resume a paused refresh cycle.
```javascript
this.resumeRefresh();
```

### Events

The mixin triggers events you can listen to:

```javascript
// Listen for refresh events
this.on('refresh:start', this, this._onRefreshStart);
this.on('refresh:complete', this, this._onRefreshComplete);
this.on('refresh:error', this, this._onRefreshError);
```

## 🎨 UI Integration

### Add Refresh Controls

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

### Visual Indicators

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

## ⚙️ Advanced Features

### Intelligent Refresh

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

### Batch Operations

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

### Performance Monitoring

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

## 🐛 Troubleshooting

### Common Issues

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

### Debug Mode

Enable debug logging:
```javascript
// In your controller
init: function () {
    this._super.apply(this, arguments);
    this.refreshDebug = true; // Enable debug logs
}
```

## 📊 Performance Best Practices

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

## 🤝 Contributing

We welcome contributions:
1. Fork the repository
2. Add new features
3. Ensure backward compatibility
4. Submit pull request

## 📄 License

Licensed under AGPL-3.0. See [LICENSE](../LICENSE) for details.

## 👥 Credits

### Authors
- Polimex Dev Team

### Maintainer
- [Polimex](https://polimex.co)

## 🌐 Links

- [Documentation](https://polimex.co/docs/refresh-mixin)
- [Examples](https://github.com/polimex/odoo-apps/tree/18.0/refresh_mixin/examples)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/refresh_mixin/)

---

For more information, visit [polimex.co](https://polimex.co)