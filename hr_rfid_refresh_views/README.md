# RFID Refresh Views

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-18.0.1.0.0-green.svg)](https://apps.odoo.com)

Auto-refresh functionality for real-time RFID monitoring views.

## 🎯 Overview

RFID Refresh Views adds automatic refresh capabilities to RFID-related views in Odoo, enabling real-time monitoring of access events, door statuses, and system alerts without manual page reloads. Essential for security monitoring and control room operations.

## ✨ Key Features

### Auto-Refresh Views
- **Event Lists**: Live access event updates
- **Door Status**: Real-time door state monitoring
- **Controller Status**: Online/offline indicators
- **Alarm Monitoring**: Instant alarm notifications

### Configurable Intervals
- **Per-View Settings**: Different refresh rates
- **User Preferences**: Personal refresh settings
- **Performance Modes**: High/low frequency options
- **Pause/Resume**: Manual control available

### Smart Refresh
- **Change Detection**: Refresh only on changes
- **Batch Updates**: Efficient data loading
- **Focus Aware**: Pause when window inactive
- **Error Recovery**: Automatic reconnection

## 📋 Requirements

- Odoo 18.0+
- hr_rfid module
- refresh_mixin module
- Modern web browser with JavaScript

### Dependencies
```python
'depends': ['hr_rfid', 'refresh_mixin']
```

## 🛠️ Installation

1. Install dependencies first

2. Install the module:
```bash
./odoo-bin -d your_database -i hr_rfid_refresh_views
```

3. Refresh browser to load new features

## 🔧 Configuration

### Global Settings

Configure in Settings → Technical → System Parameters:
```python
# Refresh intervals (seconds)
hr_rfid_refresh_views.event_interval = 5
hr_rfid_refresh_views.door_interval = 10
hr_rfid_refresh_views.alarm_interval = 3
hr_rfid_refresh_views.controller_interval = 30
```

### Per-View Configuration

1. **Open View**: Navigate to desired view
2. **Settings Icon**: Click refresh settings
3. **Configure**:
   - Enable/disable auto-refresh
   - Set refresh interval
   - Choose refresh mode

### User Preferences

Users can override defaults:
- My Preferences → RFID Monitoring
- Set personal refresh rates
- Enable/disable for specific views

## 📖 Usage

### Enabled Views

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

### Control Options

#### Manual Controls
- **Pause Button**: Temporarily stop refresh
- **Resume Button**: Restart auto-refresh
- **Refresh Now**: Force immediate update
- **Settings**: Adjust interval on-the-fly

#### Automatic Behaviors
- Pauses when editing records
- Resumes after save/cancel
- Stops on connection errors
- Restarts when connection restored

## 🎨 Visual Indicators

### Status Icons
- 🟢 **Green**: Auto-refresh active
- 🟡 **Yellow**: Refresh paused
- 🔴 **Red**: Connection error
- ⚪ **Gray**: Refresh disabled

### Update Animations
- Smooth fade transitions
- Row highlighting for changes
- Count badges for new items
- Progress bar for next refresh

## 🔌 Technical Details

### JavaScript Implementation

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

### Performance Optimization

```python
# Efficient data fetching
class HrRfidEvent(models.Model):
    _inherit = 'hr.rfid.event'
    
    @api.model
    def get_refresh_data(self, last_update):
        # Return only changed records
        domain = [('write_date', '>', last_update)]
        return self.search_read(domain, ['id', 'name', 'door_id'])
```

## ⚙️ Advanced Features

### Custom Refresh Logic

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

### Conditional Refresh

```python
# Server-side refresh hints
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

## 🐛 Troubleshooting

### Common Issues

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

### Debug Mode

Enable debug logging:
```javascript
// In browser console
odoo.debug = true;
localStorage.setItem('debug', 'assets,refresh');
```

## 📊 Performance Impact

### Resource Usage
- Minimal CPU impact
- Network: ~1KB per refresh
- Memory: No accumulation
- Battery: Optimized for mobile

### Best Practices
- Use appropriate intervals
- Disable for static data
- Pause when not viewing
- Filter unnecessary fields

## 🤝 Contributing

Contributions welcome:
1. Fork repository
2. Add new view support
3. Test performance impact
4. Submit pull request

## 📄 License

Licensed under AGPL-3.0. See [LICENSE](../LICENSE) for details.

## 👥 Credits

### Authors
- Polimex Dev Team

### Maintainer
- [Polimex](https://polimex.co)

## 🌐 Links

- [Documentation](https://polimex.co/docs/rfid-refresh)
- [Performance Guide](https://polimex.co/docs/rfid-refresh-performance)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/hr_rfid_refresh_views/)

---

For more information, visit [polimex.co](https://polimex.co)