# User Manual - RFID Access Control System

## Table of Contents

1. [Introduction to Odoo 18](#introduction-to-odoo-18)
2. [About Polimex Holding Ltd](#about-polimex-holding-ltd)
3. [RFID System Overview](#rfid-system-overview)
4. [Interface Organization](#interface-organization)
5. [Events](#events)
6. [Card Management](#card-management)
7. [Access Control](#access-control)
8. [Alarm System](#alarm-system)
9. [Hardware Manager](#hardware-manager)
10. [Configuration](#configuration)

---

## Introduction to Odoo 18

Odoo 18 is a modern open-source ERP (Enterprise Resource Planning) system that provides a comprehensive solution for managing business processes. The system integrates modules for accounting, human resources management, sales, warehouse management, manufacturing, and many others into a single platform.

Odoo is characterized by:
- Modular architecture - install only the modules you need
- Intuitive web interface, accessible from any device
- Customization capabilities to meet specific business needs
- Integration between all modules for seamless data exchange

## About Polimex Holding Ltd

Polimex Holding Ltd is a leading Bulgarian company specializing in the development of innovative solutions for physical access control and security systems integration. The company is an official Odoo partner for Bulgaria and has Odoo certified functional experts. Polimex is the first company in the Balkans with three Odoo 18 functional experts.

With over 20 years of experience in the field, the company is a proven leader in providing comprehensive solutions for:

- RFID technology access control systems
- ERP system integration
- Time and attendance solutions
- Visitor management systems
- Intelligent building automation solutions

The RFID access control module is developed by Polimex's expert team and represents a professional solution for managing physical access in organizations, fully integrated with Odoo.

## RFID System Overview

### Key Features

The RFID access control system is a comprehensive solution that enables:

- **Physical access management** - control who, when, and where has access to your premises
- **Human resources integration** - automatic synchronization with employees in Odoo
- **Real-time monitoring** - observe events and door status live
- **Flexible time schedules** - create complex access schedules as needed
- **Visitor management** - temporary cards for guests and contractors
- **Detailed reports** - analyze access and attendance data

### Supported Hardware

The system supports the following controller models:
- iCON50 - basic controller for 1 door
- iCON110 - controller for 2 doors
- iCON115 - advanced controller for 2 doors
- iCON130 - controller for 4 doors
- iCON180 - professional controller for 4 doors

## Interface Organization

Upon entering the RFID system, the main menu is located at the top of the screen. It is organized into the following main sections:

### Main Menu - RFID System

1. **Events** - view all system events
2. **Card Management** - manage RFID cards and their holders
3. **Access Control** - configure access rights
4. **Alarm System** - manage alarm lines
5. **Hardware Manager** - configure physical devices
6. **Configuration** - general system settings

### Access Levels

The system has three main access levels:

1. **Guard** - can view user events
2. **Officer** - can manage cards and basic settings
3. **Manager** - full access to all functions

## Events

### User Events

This is the main screen for real-time system monitoring. Here you can see:

- **Event time** - exact time of each action
- **Employee/Contact** - who performed the action
- **Door** - which door they passed through
- **Reader** - which reader was used (entry/exit)
- **Action** - result of card presentation:
  - *Access granted* - successful access
  - *Access denied* - invalid card
  - *Access denied T/S* - outside allowed time
  - *Access denied APB* - anti-passback violation

**Filtering and searching:**
- Use filters to view events for a specific period
- Search by employee name, card number, or door
- Group by date, employee, or door for better analysis

### System Events

Technical events from hardware:
- Controller startup/restart
- Connection loss
- Connection recovery
- Hardware errors and warnings

### Commands

View commands sent to controllers:
- Door opening
- Settings changes
- Data synchronization
- Execution status (successful/unsuccessful)

## Card Management

### Cards

Central location for managing all RFID cards in the system.

**Creating a new card:**
1. Click the "Create" button
2. Enter the 10-digit card number
3. Select card type (standard/visitor)
4. Assign owner - employee or contact
5. Set validity period (if necessary)

**Important fields:**
- **Card number** - unique 10-digit code
- **Reference** - convenient name (e.g., "Pass #37")
- **Card type** - determines which doors can be used
- **Active from/to** - validity period
- **Cloud card** - for online controllers (usually YES)

### Employees

Integration with human resources module:
- View all employees
- Assign cards to employees
- Manage access groups
- Synchronization with departments

### Departments

Organizational structure:
- Group employees by departments
- Assign standard access rights
- Hierarchical structure

### Partners

External personnel management:
- Visitors
- Contractors
- Suppliers
- Temporary staff

## Access Control

### Access Groups

Access groups are the main mechanism for managing rights.

**Creating an access group:**
1. Give a descriptive name (e.g., "Working hours access")
2. Add doors to the group
3. Select time schedule for each door
4. Assign employees or departments

**Advanced features:**
- **Event delay** - anti-passback protection
- **Inheritance** - one group can include rights from another
- **Alarm rights** - who can arm/disarm alarms

### Time Schedules

Define when access is allowed.

**Time schedule structure:**
- 7 days of the week
- Up to 4 time intervals per day
- Special holiday settings

**Examples:**
- *Working hours* - Mon-Fri 08:00-18:00
- *24/7 access* - Permanent access
- *Night shift* - 22:00-06:00 every day

### Work Codes

Special codes for activity tracking:
- Work start
- Work end
- Break
- Business exit

### Zones

Logical grouping of doors by areas.

**Zone functions:**
- Track who is currently inside
- Zone-level anti-passback
- Automatic system logout upon exit
- Entry/exit notifications

## Alarm System

### Alarm Lines

Physical sensors connected to controllers:
- "Door open" sensor
- "Door forced" sensor
- PIR motion sensors
- Fire detection sensors

**Settings:**
- Normally open/closed contact
- Alarm delay
- Actions on alarm

### Alarm Line Groups

Grouping alarm lines for management:
- Arm/disarm entire group
- Common notifications
- Coordinated actions

## Hardware Manager

### Modules (Webstacks)

Network modules that connect controllers to Odoo.

**Adding a new module:**
1. Enter name and IP address
2. Set 6-digit serial number
3. Change security key (from 0000)
4. Test connection

### Module Discovery

Automatic search in local network:
1. Click "Scan"
2. Wait for modules to appear
3. Select and add desired ones

### Controllers

Physical devices controlling doors.

**Important settings:**
- Model and version
- Number of doors
- Number of readers
- Operating mode

### Doors

Configuration for each door:
- Name and number
- Unlock time (3-15 sec)
- Accepted card types
- APB mode

### Readers

RFID card readers:
- Entry/exit
- Type and format
- Light and sound signaling

### Emergency Groups

Predefined scenarios:
- Open all doors in case of fire
- Lock down in case of threat
- Partial evacuation

## Configuration

### General Settings

Global system parameters:
- Card format (Wiegand 34)
- Old events cleanup
- Notification settings
- Integration with other modules

**Important parameters:**
- **Keep events** - how many days to store data
- **Check for duplicate doors** - prevents errors
- **Automatic synchronization** - update frequency

---

## Frequently Asked Questions

**Q: How do I add a new employee to the system?**
A: Employees are added through the HR module. Then assign them a card through the Cards menu.

**Q: The card doesn't work at the door?**
A: Check:
1. Is the card active?
2. Are we in the correct time period?
3. Does the employee have access to this door?
4. Is the card type correct for the door?

**Q: How do I give temporary access to a visitor?**
A: Create a "Visitor" type card, set a validity period, and link it to a contact (not an employee).

---

For technical support: support@polimex.co