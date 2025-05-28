# RFID Attendance

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-18.0.1.0.0-green.svg)](https://apps.odoo.com)

Seamless integration between RFID access control and Odoo HR attendance tracking.

## 🎯 Overview

RFID Attendance bridges the gap between physical access control and time tracking, automatically creating attendance records from RFID door events. It supports multiple check-in/out locations, zone-based attendance, and automatic session closure.

## ✨ Key Features

### Attendance Automation
- **Automatic Check-in/out**: Convert RFID events to attendance records
- **Zone-based Tracking**: Different zones for different attendance types
- **Multi-location Support**: Track attendance across multiple sites
- **Flexible Rules**: Configure which doors/zones create attendance

### Smart Processing
- **Event Filtering**: Ignore rapid consecutive events
- **Session Management**: Automatic session closure after timeout
- **Break Handling**: Support for multiple check-ins/outs per day
- **Overtime Calculation**: Automatic overtime tracking

### Integration Features
- **Real-time Sync**: Instant attendance from access events
- **Bulk Processing**: Handle high-volume event streams
- **Error Recovery**: Resilient to network/system issues
- **Multi-company**: Separate attendance per company

### Reporting
- **Attendance Reports**: Standard Odoo attendance reports
- **RFID Event Correlation**: Link attendance to access events
- **Exception Reporting**: Missing check-outs, anomalies
- **Export Capabilities**: Excel, CSV exports

## 📋 Requirements

- Odoo 18.0+
- hr_rfid module installed and configured
- hr_attendance module (Odoo standard)

### Dependencies
```python
'depends': ['hr_rfid', 'hr_attendance']
```

## 🛠️ Installation

1. Install the hr_rfid module first (if not already installed)

2. Install this module:
```bash
./odoo-bin -d your_database -i hr_attendance_multi_rfid
```

3. Configure attendance zones in existing RFID setup

## 🔧 Configuration

### Zone Configuration

1. **Navigate to**: RFID → Configuration → Zones
2. **Enable Attendance**: Check "Attendance Zone" on relevant zones
3. **Set Type**: Choose attendance behavior:
   - `auto`: Automatic in/out detection
   - `in`: Always check-in
   - `out`: Always check-out
   - `toggle`: Alternate between in/out

### Door Assignment

1. **Assign Zones to Doors**: RFID → Doors → Edit
2. **Select Zone**: Choose attendance-enabled zone
3. **Save**: Doors in this zone will generate attendance

### Employee Setup

1. **RFID Cards**: Ensure employees have active RFID cards
2. **Working Hours**: Set employee working schedules
3. **PIN Codes**: Optional PIN for attendance validation

### System Parameters

Configure in Settings → Technical → System Parameters:

```
# Minimum time between attendance events (seconds)
hr_attendance_multi_rfid.min_time_between_events: 60

# Auto check-out after hours
hr_attendance_multi_rfid.auto_checkout_hours: 12

# Allow multiple check-ins per day
hr_attendance_multi_rfid.allow_multiple_sessions: True
```

## 📖 Usage

### Automatic Attendance

1. **Employee enters**: Scans card at entrance
2. **System creates**: Check-in record automatically
3. **Employee exits**: Scans card at exit
4. **System creates**: Check-out record

### Manual Overrides

Managers can still:
- Edit attendance records
- Add missing entries
- Correct errors
- Override automatic entries

### Monitoring

1. **Real-time View**: Attendance → Dashboard
2. **Who's Present**: See current on-site employees
3. **Event History**: Track all RFID events
4. **Anomalies**: Review attendance exceptions

## 🔌 API Extension

### Custom Event Processing

```python
class CustomAttendance(models.Model):
    _inherit = 'hr.attendance'
    
    def process_rfid_event(self, event):
        # Custom logic before standard processing
        if self.custom_validation(event):
            return super().process_rfid_event(event)
```

### Zone Handlers

```python
# Custom zone attendance logic
class CustomZone(models.Model):
    _inherit = 'hr.rfid.zone'
    
    def get_attendance_action(self, employee, last_attendance):
        # Custom logic for check-in/out decision
        return 'check_in' or 'check_out'
```

## 🐛 Troubleshooting

### Common Issues

1. **No attendance created**
   - Check zone configuration
   - Verify door has attendance zone
   - Confirm employee has valid card
   - Check system parameters

2. **Duplicate entries**
   - Increase min_time_between_events
   - Check for multiple doors in same zone
   - Review event processing logs

3. **Wrong in/out detection**
   - Verify zone type settings
   - Check last attendance state
   - Review employee schedule

### Debug Mode

Enable detailed logging:
```python
# In Odoo config
log_handler = hr_attendance_multi_rfid:DEBUG
```

## ⚙️ Advanced Features

### Multi-Zone Attendance

Configure complex scenarios:
- Entry zones (parking → building → office)
- Break areas with different rules
- Restricted zones with no attendance

### Shift Management

Integration with hr_attendance features:
- Shift planning
- Overtime rules
- Break policies
- Holiday handling

### Notifications

Set up alerts for:
- Missing check-outs
- Overtime threshold
- Unusual patterns
- System errors

## 📊 Reports

### Standard Reports
- Daily attendance summary
- Monthly timesheets
- Overtime analysis
- Late arrival tracking

### Custom Reports
- RFID event correlation
- Zone utilization
- Access vs attendance comparison
- Exception reports

## 🤝 Contributing

We welcome contributions! Please:
1. Fork the repository
2. Create feature branch
3. Add tests for new features
4. Submit pull request

## 📄 License

This module is licensed under AGPL-3.0. See [LICENSE](../LICENSE) for details.

## 👥 Credits

### Authors
- Polimex Dev Team

### Contributors
- See [contributors](https://github.com/polimex/odoo-apps/contributors)

### Maintainer
- [Polimex](https://polimex.co)

## 🌐 Links

- [Documentation](https://polimex.co/docs/rfid-attendance)
- [Support](https://polimex.co/support)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/hr_attendance_multi_rfid/)

---

For more information, visit [polimex.co](https://polimex.co)