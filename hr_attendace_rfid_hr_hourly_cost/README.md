# RFID Hourly Cost

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-18.0.1.0.0-green.svg)](https://apps.odoo.com)

Hourly cost tracking integration for RFID-based attendance records.

## 🎯 Overview

RFID Hourly Cost bridges RFID attendance tracking with hourly cost calculations, providing accurate labor cost analysis based on actual worked hours captured through RFID access control systems. It automatically calculates labor costs for projects, departments, and cost centers.

## ✨ Key Features

### Cost Tracking
- **Automatic Calculation**: Real-time hourly cost computation
- **Multi-rate Support**: Different rates for regular/overtime
- **Department Costs**: Track costs by department
- **Project Allocation**: Assign costs to projects

### Integration
- **RFID Attendance**: Seamless integration with RFID attendance
- **Payroll Ready**: Export data for payroll processing
- **Accounting Links**: Direct posting to accounting
- **Timesheet Sync**: Update timesheets automatically

### Reporting
- **Cost Analytics**: Detailed cost breakdowns
- **Department Comparison**: Compare labor costs
- **Project Profitability**: Track project labor costs
- **Budget vs Actual**: Monitor cost overruns

## 📋 Requirements

- Odoo 18.0+
- hr_hourly_cost module
- hr_attendance_late module
- Python 3.8+

### Dependencies
```python
'depends': ['hr_hourly_cost', 'hr_attendance_late']
'auto_install': True  # Installs automatically when both dependencies are present
```

## 🛠️ Installation

This module auto-installs when both dependencies are installed:

```bash
# Install dependencies first
./odoo-bin -d your_database -i hr_hourly_cost,hr_attendance_late

# Module will auto-install
```

## 🔧 Configuration

### Employee Setup

1. **Navigate to**: Employees → Employee → HR Settings tab
2. **Configure**:
   - Hourly Cost: Base hourly rate
   - Overtime Rate: Overtime multiplier
   - Currency: Cost currency
   - Cost Center: Default allocation

### Attendance Configuration

Set up in hr_attendance_late module:
- Work schedules
- Overtime rules
- Break deductions
- Shift differentials

### Cost Rules

Configure in Settings → Attendance → Hourly Cost:
```python
# Example configuration
regular_hours_limit = 40  # Weekly regular hours
overtime_multiplier = 1.5  # Overtime rate multiplier
include_breaks = False  # Include breaks in cost
```

## 📖 Usage

### Automatic Calculation

Costs are calculated automatically when:
1. Employee checks in/out via RFID
2. Attendance records are created
3. Late attendance is processed

### View Costs

1. **Individual Employee**
   - Employee form → Attendance tab
   - View hourly costs summary
   - Check detailed breakdown

2. **Department Level**
   - Reporting → Attendance → Department Costs
   - Select period and department
   - View aggregated costs

3. **Project Costs**
   - Project → Labor Costs tab
   - See allocated employee costs
   - Track budget utilization

## 📊 Reports

### Cost Summary Report
```
Employee Cost Summary
Period: January 2024

Employee          Regular Hours    OT Hours    Total Cost
John Doe          160             10          $3,450.00
Jane Smith        155             15          $3,875.00
Department Total  315             25          $7,325.00
```

### Detailed Analysis
- Hourly breakdown
- Cost center allocation
- Overtime analysis
- Attendance patterns vs cost

## 🔌 API Reference

### Cost Calculation
```python
# Get employee hourly cost
employee = self.env['hr.employee'].browse(employee_id)
attendance = self.env['hr.attendance'].browse(attendance_id)

# Calculate cost for attendance period
regular_cost = attendance.worked_hours * employee.hourly_cost
overtime_cost = attendance.overtime_hours * employee.hourly_cost * 1.5
total_cost = regular_cost + overtime_cost
```

### Bulk Processing
```python
# Process monthly costs
attendances = self.env['hr.attendance'].search([
    ('check_in', '>=', month_start),
    ('check_in', '<', month_end)
])
attendances.calculate_hourly_costs()
```

## 🐛 Troubleshooting

### Common Issues

1. **Costs not calculating**
   - Check employee hourly rate is set
   - Verify attendance records exist
   - Ensure work schedule is configured

2. **Wrong cost amounts**
   - Verify hourly rates
   - Check overtime rules
   - Review calculation settings

3. **Missing in reports**
   - Check date filters
   - Verify employee is active
   - Ensure proper permissions

## ⚙️ Advanced Features

### Custom Cost Rules
```python
class HrAttendanceExtra(models.Model):
    _inherit = 'hr.attendance'
    
    def _compute_hourly_cost(self):
        # Add custom logic
        if self.is_holiday:
            return self.worked_hours * self.employee_id.hourly_cost * 2
        return super()._compute_hourly_cost()
```

### Multi-Currency Support
- Configure rates per currency
- Automatic conversion
- Historical rate tracking

## 🤝 Contributing

Contributions welcome:
1. Fork repository
2. Create feature branch
3. Add tests
4. Submit pull request

## 📄 License

Licensed under AGPL-3.0. See [LICENSE](../LICENSE) for details.

## 👥 Credits

### Authors
- Polimex Dev Team

### Maintainer
- [Polimex](https://polimex.co)

## 🌐 Links

- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/hr_attendace_rfid_hr_hourly_cost/)
- [Support](https://polimex.co/support)

---

For more information, visit [polimex.co](https://polimex.co)