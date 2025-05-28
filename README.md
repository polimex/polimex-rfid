# Polimex RFID Access Control Suite for Odoo

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Odoo Version](https://img.shields.io/badge/Odoo-18.0-875A7B.svg)](https://www.odoo.com/)
[![Company](https://img.shields.io/badge/Company-Polimex-orange.svg)](https://polimex.co)

A comprehensive suite of Odoo modules for professional RFID-based access control, attendance tracking, and facility management.

## 🎯 Overview

The Polimex RFID Suite provides enterprise-grade access control integration for Odoo, supporting various RFID hardware controllers and offering extensive features for managing employee access, visitor management, attendance tracking, and specialized applications like vending machines and voting systems.

## 📦 Modules

### Core RFID Modules

| Module | Description | Version |
|--------|-------------|---------|
| [**hr_rfid**](hr_rfid/) | Main RFID Access Control module with hardware integration | 18.0.2.2.0 |
| [**hr_rfid_site_manager**](hr_rfid_site_manager/) | Multi-site management and hierarchical organization | 18.0.1.0.0 |
| [**hr_rfid_portal**](hr_rfid_portal/) | Web portal interface for RFID card management | 18.0.0.1.0 |
| [**hr_rfid_refresh_views**](hr_rfid_refresh_views/) | Auto-refresh functionality for real-time monitoring | 18.0.1.0.0 |

### Attendance Integration

| Module | Description | Version |
|--------|-------------|---------|
| [**hr_attendance_multi_rfid**](hr_attendance_multi_rfid/) | RFID integration with Odoo attendance | 18.0.1.0.0 |
| [**hr_attendance_late**](hr_attendance_late/) | Late attendance calculations and reports | 18.0.1.0.0 |
| [**hr_attendace_rfid_hr_hourly_cost**](hr_attendace_rfid_hr_hourly_cost/) | Hourly cost tracking for attendance | 18.0.1.0.0 |

### Service Management

| Module | Description | Version |
|--------|-------------|---------|
| [**rfid_service_base**](rfid_service_base/) | Base structures for visitor/service management | 18.0.0.2.0 |
| [**rfid_service_portal**](rfid_service_portal/) | Portal extensions for service management | 18.0.0.1.0 |
| [**rfid_service_zpl_labels**](rfid_service_zpl_labels/) | ZPL wristband label printing | 18.0.0.1.0 |

### Specialized Applications

| Module | Description | Version |
|--------|-------------|---------|
| [**hr_rfid_vending**](hr_rfid_vending/) | Vending machine integration | 18.0.1.6.0 |
| [**hr_rfid_vertical_elections**](hr_rfid_vertical_elections/) | Voting system using RFID | 18.0.1.0.0 |
| [**polimex_ip_cam**](polimex_ip_cam/) | IP camera integration with ANPR | 18.0.1.0.0 |
| [**rfid_pms_base**](rfid_pms_base/) | Property Management System integration | 18.0.0.1.0 |

### Import Tools

| Module | Description | Version |
|--------|-------------|---------|
| [**hr_rfid_andromeda_import**](hr_rfid_andromeda_import/) | Import from Andromeda system | 18.0.1.1.0 |
| [**hr_rfid_old_cloud_import**](hr_rfid_old_cloud_import/) | Legacy cloud system import | 18.0.1.1.0 |

### Utilities

| Module | Description | Version |
|--------|-------------|---------|
| [**refresh_mixin**](refresh_mixin/) | Mixin for auto-refresh functionality | 18.0.1.0.0 |

## 🚀 Features

- **Hardware Support**: Compatible with iCON50, iCON110, iCON115, iCON130, iCON180 controllers
- **Multi-Company**: Full multi-company support with data isolation
- **Real-time Monitoring**: Live event tracking and door status monitoring
- **Access Management**: Time-based schedules, access groups, and zone management
- **Attendance Integration**: Seamless integration with Odoo HR attendance
- **Visitor Management**: Temporary access cards with time/visit limitations
- **Reporting**: Comprehensive reports for access logs, attendance, and analytics
- **Security**: Row-level security, audit trails, and encrypted communication
- **Scalability**: Supports thousands of doors and cards across multiple locations

## 📋 Requirements

- Odoo 18.0
- PostgreSQL 12+
- Python 3.8+
- Compatible RFID hardware controllers

## 🛠️ Installation

1. Clone the repository to your Odoo addons path:
```bash
git clone https://github.com/polimex/odoo-apps.git /path/to/addons/polimex
```

2. Update the addons path in your Odoo configuration file:
```ini
addons_path = /path/to/addons/polimex,/path/to/odoo/addons
```

3. Restart Odoo and update the apps list:
```bash
./odoo-bin -d your_database --update=apps_list
```

4. Install the required modules through the Odoo Apps interface.

## 🔧 Configuration

### Basic Setup

1. **Install hr_rfid module** - This is the core module required by most others
2. **Configure webstacks** - Set up communication with your RFID controllers
3. **Define doors and readers** - Map your physical hardware
4. **Create access groups** - Define who can access what areas
5. **Assign cards** - Issue RFID cards to employees or visitors

### Hardware Setup

Refer to the [hr_rfid documentation](hr_rfid/README.md) for detailed hardware setup instructions.

## 📖 Documentation

Each module contains its own README.md with specific documentation:

- Installation instructions
- Configuration guide
- Usage examples
- API reference (where applicable)
- Troubleshooting tips

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines before submitting pull requests.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🐛 Bug Reports

Please report bugs using the GitHub issue tracker. Include:
- Odoo version
- Module version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error logs (if any)

## 📄 License

This project is licensed under the AGPL-3.0 License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **Polimex Dev Team** - *Initial work and maintenance*

## 🌐 Links

- [Polimex Website](https://polimex.co)
- [Odoo Apps Store](https://apps.odoo.com/apps/browse?repo_maintainer_id=134125)
- [GitHub Repository](https://github.com/polimex/odoo-apps)

## 💡 Support

For support and custom development:
- Email: support@polimex.co
- Website: https://polimex.co

---

Made with ❤️ by [Polimex](https://polimex.co)