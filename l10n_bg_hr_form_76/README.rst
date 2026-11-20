===========================
Attendance Form 76 Bulgaria
===========================

The attendance sheet of a department for a month (form 76, "Таблица за
отчитане явяването/неявяването на работа"): every person under contract in
the month, a cell per day with the hours worked or the letter of the
absence, and the totals the NSI template asks for.

Usage
=====

Print the sheet from **Attendances -> Reporting -> Generate Form 76**: pick
the year, the month and the departments.

Which days Form 76 marks
------------------------

Leave is marked on the days it was asked for. Non-working days ("Н") are
the days off of the employee's schedule and the public holidays of the
employee's own company, as they live them, in their own
**Timezone** (employee form, *Settings* tab) - the same days the worked
hours in the form are filed under. A night shift that begins at midnight
is therefore marked on its own day, not on the evening before.

What the columns hold
---------------------

The columns follow the NSI template of the attendance sheet
("Таблица за отчитане явяването/неявяването на работа").

- **Who is on the sheet:** everybody under contract on at least one day of
  the month, including a person who left during the month and was archived,
  and a person hired during it; nobody who left before the month or was hired
  after it. The days outside the contract are blank, not absences, and the
  norm counts only the working days of the contract. This needs the
  **Contract Start Date** (and the end date for a person who left) on the
  employee; an employee without contract dates is on every month's sheet
  while active.
- **Days off ("Н")** are those of the working schedule the person had in that
  month, so a schedule changed later does not change the sheet of a past
  month.
- **Days of leave** show the Form 76 letter of the time-off type. With the
  Bulgarian time-off catalog installed, a time-off type has two Form 76
  letter fields; the letter filled in the catalog's field is printed, the
  sheet's own field is used when the catalog's one is empty, and the form of
  the type shows the sheet's own field only then. A letter typed on a Latin
  keyboard ("O" for "О") is saved as the Cyrillic one of the legend, so its
  days are counted in their column; "NA", the mark of a type without a
  letter, stays as it is.
- **Position and department** are those of the employee's contract version
  in force on the last day of the month, so the sheet of a past month shows
  the position held then, not today's.
- **A working day** shows every hour worked that day, overtime included.
- **"Всичко"** (hours worked) holds the hours of the working days plus the
  hours worked on days off and holidays; **"в т.ч. извънредни"** is the part
  of it that is overtime: overtime on working days plus the hours on days off
  and holidays.
- Hours are rounded day by day, half up, as the day cells are; with
  precision 0 every column prints whole numbers.
- **"Частични"** (under "Неотработени човекочасове") holds the scheduled hours
  not worked on days the person came - arriving late, leaving early, a gap in
  the day (a lunch break is not one of them) - and approved time off
  for part of the day (half a day or some hours) - leave is not worked time.
- **"в т.ч. целодневен престой"** stays empty: standstill caused by the
  employer is not recorded in the system; fill it in by hand if there was
  any.
- With **fixed hours per day** set in the wizard, every worked day shows that
  figure, and neither the overtime nor the missed hours of a working day are
  counted; hours worked on a day off still are.

Credits
=======

Authors
-------

* Polimex Holding Ltd. - https://polimex.co
