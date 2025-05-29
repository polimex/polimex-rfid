# Late Attendance

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-18.0.1.0.0-green.svg)](https://apps.odoo.com)

Advanced attendance calculations with late arrival tracking and department-based rules.

## 🎯 Overview

Late Attendance extends Odoo's attendance system with sophisticated late arrival tracking, grace periods, overtime calculations, and department-specific attendance rules. It provides comprehensive reporting on attendance patterns and helps enforce attendance policies.

## ✨ Key Features

### Late Tracking
- **Automatic Detection**: Identifies late arrivals based on work schedules
- **Grace Periods**: Configurable tolerance before marking as late
- **Department Rules**: Different late policies per department
- **Excuse Management**: Track and approve late arrival reasons

### Calculations
- **Work Hours**: Accurate worked time calculations
- **Overtime**: Automatic overtime detection and calculation
- **Break Time**: Configurable break deductions
- **Shift Differential**: Support for different shift timings

### Reporting
- **Late Summary**: Daily/monthly late arrival reports
- **Department Analytics**: Compare attendance across departments
- **Individual Reports**: Employee attendance history
- **Export Options**: Excel and PDF export capabilities

### Integration
- **RFID Events**: Works with hr_attendance_multi_rfid
- **Payroll Ready**: Late deductions for payroll
- **Email Alerts**: Automated notifications for violations
- **Manager Dashboard**: Real-time attendance monitoring

## 📋 Requirements

- Odoo 18.0+
- hr_attendance module
- hr module
- Python 3.8+

### Optional Dependencies
- hr_attendance_multi_rfid (for RFID integration)
- hr_payroll (for salary deductions)

## 🛠️ Installation

1. Install the module:
```bash
./odoo-bin -d your_database -i hr_attendance_late
```

2. Configure attendance rules in Settings

## 🔧 Configuration

### Global Settings

Navigate to Settings → Attendance → Late Attendance:

```python
# Attendance parameters
late_attendance_grace_minutes = 5  # Grace period in minutes
late_attendance_minimum_minutes = 15  # Minimum late to count
late_attendance_round_to = 15  # Round late minutes to
```

### Department Configuration

1. **Go to**: Employees → Departments
2. **Edit Department**: Set attendance rules
   - Grace period (minutes)
   - Late penalty rules
   - Specific work schedules
   - Notification settings

### Work Schedules

Configure in Settings → Technical → Resource Calendar:
- Set exact work hours
- Define break times
- Configure holidays
- Set timezone

## 📖 Usage

### Employee View

Employees can:
1. View their attendance history
2. See late arrival records
3. Submit late excuses
4. Check accumulated late time

### Manager Functions

1. **Monitor Dashboard**
   - Real-time attendance status
   - Late arrivals alerts
   - Department overview

2. **Approve Excuses**
   - Review late reasons
   - Approve/reject excuses
   - Add manager notes

3. **Generate Reports**
   - Late attendance summary
   - Department comparison
   - Individual employee reports

### HR Functions

1. **Policy Management**
   - Set attendance rules
   - Configure penalties
   - Define grace periods

2. **Bulk Operations**
   - Approve multiple excuses
   - Export attendance data
   - Generate payroll deductions

## 📊 Reports

### Standard Reports

1. **Late Attendance Summary**
   - Employee name
   - Department
   - Late occurrences
   - Total late minutes
   - Excused/unexcused

2. **Department Analysis**
   - Average late per department
   - Trends over time
   - Comparison charts

3. **Individual Report**
   - Detailed attendance history
   - Late patterns
   - Excuse history

### Custom Reports

Create custom reports using:
```python
# Get late attendance data
late_records = self.env['hr.attendance'].search([
    ('employee_id', '=', employee_id),
    ('late_minutes', '>', 0),
    ('check_in', '>=', date_from),
    ('check_in', '<=', date_to)
])
```

## 🔧 Advanced Configuration

### Calculation Methods

```python
# In attendance settings
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    attendance_calculation_method = fields.Selection([
        ('actual', 'Actual Time'),
        ('scheduled', 'Scheduled Time'),
        ('flexible', 'Flexible Hours')
    ])
```

### Notifications

Configure automated emails:
```xml
<!-- Email template for late arrival -->
<record id="email_template_late_arrival" model="mail.template">
    <field name="name">Late Arrival Notification</field>
    <field name="model_id" ref="hr_attendance.model_hr_attendance"/>
    <field name="subject">Late Arrival on ${object.check_in}</field>
</record>
```

### Integration Hooks

```python
# Override to add custom logic
class HrAttendance(models.Model):
    _inherit = 'hr.attendance'
    
    def _compute_late_minutes(self):
        # Custom late calculation
        super()._compute_late_minutes()
        # Add your logic here
```

## 🐛 Troubleshooting

### Common Issues

1. **Late not calculated**
   - Check work schedule configuration
   - Verify timezone settings
   - Ensure calendar is assigned to employee

2. **Wrong late minutes**
   - Check grace period settings
   - Verify break time configuration
   - Review calculation method

3. **Reports missing data**
   - Ensure attendance records exist
   - Check date range filters
   - Verify employee permissions

### Debug Mode

Enable detailed logging:
```python
# In Odoo config
log_handler = hr_attendance_late:DEBUG
```

## 📈 Best Practices

1. **Set Realistic Grace Periods**
   - Consider commute variations
   - Account for clock synchronization
   - Balance strictness with fairness

2. **Regular Monitoring**
   - Review reports weekly
   - Address patterns early
   - Provide feedback to employees

3. **Clear Policies**
   - Document attendance rules
   - Communicate changes
   - Apply consistently

## 🤝 Contributing

We welcome contributions:
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

- [Documentation](https://polimex.co/docs/late-attendance)
- [Support](https://polimex.co/support)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/hr_attendance_late/)

---

For more information, visit [polimex.co](https://polimex.co)