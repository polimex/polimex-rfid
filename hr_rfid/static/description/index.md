<style>
    body {
        font-family: Arial;
        font-size: 17px;
    }
    a {
        color: #054279;
        text-decoration: none;
    }

    a:hover {
        color: black;
    }

table.gridtable {
    color:#333333;
    border-width: 1px;
    border-color: #666666;
    border-collapse: collapse;
}
table.gridtable th {
    border-width: 1px;
    padding: 8px;
    border-style: solid;
    border-color: #666666;
    background-color: #dedede;
}
table.gridtable td {
    border-width: 1px;
    padding: 8px;
    border-style: solid;
    border-color: #666666;
    background-color: #ffffff;
}

h2 {
  text-align: center;
}

h2:hover {
  text-shadow: 2px 2px grey;
}

img {
  border-radius: 5px;
}

</style>

<div id="top"></div><div id="top"></div>

<center>
![](./icon.png)

# RFID Access Control
</center>

---

## Brief description

RFID Access App is a TCP/IP interface Module with which you can receive information, real time, about all employees or partners of the company - their 
current access by authorization in building/rooms, done work, or employee's current condition - who is sick, on a paid leave or didn't come to work.
The Module is a required support for the Polimex Holding's controller (which uses our http based WEBSDK protocol) and LAN Modules.


## Features

With the RFID Access App, you can:

* Gain information about the entrance of the company's building/rooms or specific places;

* Create different access groups, and set each employee or partner to some of those groups, where each access group corresponds to access to one or more doors of the company's building;

* Give expiration date of a given access group;

* Import cards and their owners using excel, or csv files, or create them manually;

* Control the access of each department in the company;

* Setting Time schedules;

* ... and optionally you can get access to the vending machine at the office;

And all that you can get on any platform, from anywhere - real time.

<a href="#explained">Click</a> here to learn more about the features.

<div id="install"></div>
## Steps of installation

*	<a href="#basics">**Basics**</a>
*	<a href="#sdk">**SDK Settings(Activation of Polimex TCP/IP Interface Module)**</a>
*	<a href="#add">**Adding a card**</a>

---

<div id="basics"></a>


### Basics
1. Go to your Odoo page, and login. (make sure you have [odoo](https://www.odoo.com/documentation/12.0/setup/install.html))

![](./important.png) If you have any problems during the installation of odoo, you can get help from the users in [**odoo's forum**](https://www.odoo.com/forum/help-1), or in [stack**overflow**](https://stackoverflow.com/questions/tagged/odoo-12).

2. Go to the menu at the top left corner and click on it.

![](./odoo_index.png)

3. You will get a list with sub-menus. Click on the Apps menu.

![](./odoo_index_menu_options.png)

![](./odoo_index_apps_menu_option.png)

4. Remove the apps tag, and write rfid.

![](./apps_index_search_clean.png)

![](./important.png) Your Apps page will look different, but you can modify it by creating a list of your favorite apps.

5. Click search (or press enter).

6. You will get two results, the RFID attendance and RFID Access control.

7. Click on the installation icon of RFID Access Control.

![](./result_search_rfid.png)

8. Now you need to wait odoo to install all dependencies.

9. After installation, odoo will redirect you back to your index page.
Click again to the top left corner of the page. You have at least one new option - RFID System.

![](./odoo_index.png)

10. Click to the RFID System option.

![](./rfid_option.png)

11. Your page now should look like this:

![](./rfid_index.png)

#### Events
Clicking on that menu, gives you a list with other 3 sub-menus.
	
![](./events_menu.png)
	
##### User Events

Lists all times in which someone tried to enter the building/floor at some of the doors, when, number of the card, and etc.

![](./user_events.png)

##### System Events

Lists all errors raised in the system, for example if the Webstack is not active, and someone tries to get access, or someone is trying to authorize with a card, which is not in the system.

![](./system_events.png)

##### Commands

#### Cards

If you click to that menu, your page should look like this.

![](./cards_index.png)

There are two options in that page:
* Creating a card (Create button)

![](./create_card.png)

* Or importing cards (Import button)

![](./import_card.png)

Click on `Create`. You should see the following form:

![](./card_form.png)

<div id="fields"></div>
The fields included in the form, are:

| Field name  |   |
|---|---|
|Card Number	   | Number of the card  |
|Card Owner (Employee)   |  If the card is for employee of the company, you can write, or find the employee by clicking on the field. You will get a list with employees of the company. If you don't find it, click on the search option of the list. |
|Card Owner (Contact/Partner)   | If the card is for a partner of the company, again - you can write its name or select it from the list, which you get after clicking on the empty field nex2t to the label.  |
| Active     |  By default is set to active. If you want the card to become active, after specified time, change that in Active on (the next option) and uncheck option in Active.   |
|Active on    |  Sets the starting date from which the card will be active from  |
| Deactivate on | Sets the ending date, when the card will no more be active |
| Cloud Card | Because each controller has its own memory, which is limited, its possible all information about the cards to be kept in an external place - an external db. Activating this option means that after authorization with a card, the controller will not check its own memory for that card, but will search for it in that external memory. 

<a href="#top">Go back to the beginning of the page</a>

---

<div id="sdk"></div>

### SDK settings

1. Go to your Polimex TCP/IP Interface Module /Get the IP of the Module and write it to your web browser, press Enter/.

![](./polimex_index.png)

2. Go to the right top corner of the page - login, and click it.

3. The default username is 'admin' and by default there is no password.

4. There is a menu on the top page including Setup, IO Control and Device Manager.

5. Hover over Setup and find the Services option, click on it.

![](./service_menu.png)

6. Choose Enable for SDK sends events

7. Choose Enable for RPC JSON format (Odoo)

8. Change the `odoo.link` in the HTTP Server Push URL with a link or an IP to the odoo server.

9. Change the Server PORT with the Odoo's port.

10. Save the settings.

![](./polimex_settings.png)

11. Go to Device Manager -> Scan

![](./scan_modules.png)

12. Click Start, which will scan for controllers on the TCP/IP Interface Module

![](./start_scanning.png)

13. After finishing, check the system by touching your card/tag to some of the controllers.

---

![](./important.png) **For steps 14-16 you must have**

* Manager access to the RFID Access control app

* a controller connected to your Polimex TCP/IP Interface Module.

---

14. Go back to the odoo's RFID Module page.

15. Go to Settings -> Modules

![](./settings_modules.png)

16. In step 13, you made something called an event, which the TCP/IP interface Module sends to the Odoo. That Module is currently not active in Odoo, which means Odoo will not communicate with it. To set it active, click on `Set module to active`.

17. After finishing with the previous steps, it's time to add a card /cards/ to odoo.

<a href="#top">Go back to the beginning of the page</a>

---

<div id="add"></div>


### Add a card to Odoo

---

![](./important.png) **You must have** 

* Manager access to the RFID Access Control App

* a controller that can read cards connected with your Polimex TCP/IP Interface Module

![](./important.png) **Your Polimex TCP/IP Interface Module must**

* be linked with Odoo

* be active

---

1. Touch the card/tag to the controller connected to your Polimex TCP/IP Interface Module. 

2. The device will send an event to Odoo.

3. Go to the odoo's RFID page, and click to the menu **Events**, then choose **System Events**.

4. You should see an event of type `Could not find a card with this number`.

![](./card_event.png)

5. Click on the event.

![](./card_event.png)

You should see:

![](./add_card_index.png)

6. Click to the `Add card` option.

![](./add_card_option.png)

7. Fill the fields in the form. 

![](./important.png) **Make sure to choose only one type of card owner - Employee or Contact/Partner.**

![](./card_form_fields.png)

![](./important.png) If you are not sure for what each field is, click <a href="#fields">here</a>.

![](./card_form_filled.png)

8. Click on the `Add card` option.

![](./safe_card.png)

9. Now your card is created.

<a href="#top">Go back to the beginning of the page</a>

---

<div id="explained"></div>
## Features

### Card Types

| Card Type |
|---|
| Regular RFID card |
| MiFare 13/56Mhz |
| EM4100 125KHz |
| Biometric ID |
| Remote Button 1 |
| Remote Button 2 |
| Remote Button 3 |
| Remote Button 4 |
| Licence Plate |
| Barcode |

### Departments

Let's say your company is divided by departments, and each department is responsible for different kind of job in the company, and each department works at a different floor in the company's building.
So you want each employee, who works at a particular department, to have access only to the entrance of the building and entrance to the floor to which his department works.
So now we will show how to manage department access groups, and how to add each of the company employees to that group.

![](./important.png) If you don't have **RFID Access App** installed, <a href="#install">click here</a>

1. Go to your Odoo page, and login. (make sure you have [odoo](https://www.odoo.com/documentation/12.0/setup/install.html))

![](./important.png) If you have any problems during the installation of odoo, you can get help from the users in [**odoo's forum**](https://www.odoo.com/forum/help-1), or in [stack**overflow**](https://stackoverflow.com/questions/tagged/odoo-12).

2. Click on the menu (at the top left corner), and choose `Employee` from the menu.

![](./employee_menu_option.png)

3. There are three options next to the Employees logo - `Employees`, `Departments`, and `Configuration`.

![](./employees_menu_options.png)

4. Click on `Departments`. Here you can create(manually or importing with a file) departments of the company.

![](./departments_option.png)

![](./departments_company.png)

5. Let's say you want to manage the access of the `Administration` department. Click on the top right corner of the department, and choose `Settings`.

![](./departments_company_menu.png)

![](./settings_options.png)

6. There are 4 options for managing the access groups of that department.

![](./acc_group_options.png)

* Add one or more access groups; (1. Add Access Groups)

* Remove one or more access groups; (2. Remove Access Groups)

* Change the default access group; (3. Change the default access group)

* Remove the default access group; (4. Remove default access group)

**What is the difference between adding access group and changing the default access group?**

When adding an employee to some department, that employee gets the default access group of the department (each department has its own access group). If you want to add the employee to some other access group, you need to choose the option `Add Access groups` from the employee's page (check below in `Employee Access Group`)).

### Owner 

If each department (or almost each) in your company has a manager(or managers), you can give him (them) privilege, for each new employee of the department, to give access to that employee, to the building and department's floor. 

1. Go to your Odoo page, and login. (make sure you have [odoo](https://www.odoo.com/documentation/12.0/setup/install.html))

![](./important.png) If you have any problems during the installation of  odoo, you can get help from the users in [**odoo's forum**](https://www.odoo.com/forum/help-1), or in [stack**overflow**](https://stackoverflow.com/questions/tagged/odoo-12).

2. Click on the menu (at the top left corner), and choose `Settings` from the menu.

![](./settings_menu_option.png)

3. Find the option `Users & Companies` at the header of the page.

![](./users_companies_header_option.png)

4. Choose `Users`.

![](./users_choice_users_groups.png)

5. Find the name of the person, to which you want to give access. (If there are more than one person, you need to repeat that step for each of them).

![](./user_group_change_option.png)

6. Click to the name of that person.

7. Choose `Edit`.

![](./edit_user_ug.png)

8. You should see a field, with `RFID Access`.

![](./user_rfid_option_change.png)

9. There are four possible options.

* **Officer**: Allows access to the following things:
	1. Ability to view, modify, create or delete cards.
	1. Ability to view user events.
	1. Ability to view system events.
	1. Ability to add or remove access groups from employees or contacts.
	1. Ability to add or remove access groups from departments.
	1. Ability to change the default access group of a department.
* **Officer own department**: Same as above but only for the user's own department
* **Manager**: Allows access to virtually anything that the module has.
* **Manager own department**: Same as above but only for the user's own department

Choose one of them, and click `Save`.

### Employee Access Group

By default, when choosing a department of the employee, he/she gets the default access group of that department.
If you want to add more access groups(or to remove some) to that employee, you need to do that from the employee's page.

1. Go to your Odoo page, and login. (make sure you have [odoo](https://www.odoo.com/documentation/12.0/setup/install.html))

![](./important.png) If you have any problems during the installation of odoo, you can get help from the users in [**odoo's forum**](https://www.odoo.com/forum/help-1), or in [stack**overflow**](https://stackoverflow.com/questions/tagged/odoo-12).

2. Click on the menu (at the top left corner), and choose `Employees` from the menu.

![](./employees_menu_options.png)

3. Select the employee.

![](./employee_option.png)

4. Go to the `RFID Info` option.

![](./employee_rfid_info.png)

5. Select `Add Access Groups`, or `Remove Access Groups`.

![](./add_remove_acc_group_options_employee.png)

**Add Access Group**

![](./add_acc_group_employee.png)

**Remove Access Group**

![](./rem_acc_group_employee.png)

<a href="#top">Go back to the beginning of the page</a>

---

## Github

If you have any problems, questions or suggestions, you can follow us on [![](./github.png)](https://github.com/polimex/odoo_apps).

<script>

function big_images() {
    let imgs = document.getElementsByTagName("img");
    imgs = Array.prototype.slice.call(imgs);
    let filtered = imgs.filter(function(image) { return image.width > 700 });
    return filtered;
}

window.addEventListener('resize', function() {
  var imgs = big_images();

  for(let i = 0; i < imgs.length; i++) {
      imgs[i].style.width = '60%';
      imgs[i].style.height = '60%';
  }
});

document.title = 'RFID Access App';

let hrs = document.getElementsByTagName('hr');
hrs = Array.prototype.slice.call(hrs);

for(let i = 0; i < hrs.length; i++) {
	hrs[i].style.border = '1px dotted gray';
	hrs[i].style.width = '50%';
}

let tables = document.getElementsByTagName('table');
for(let i = 0; i < tables.length; i++) {
	tables[i].className = 'gridtable';
}

</script>