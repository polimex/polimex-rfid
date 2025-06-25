# Тестове за hr_attendance_late модул

## Изпълнение на тестовете

За да изпълните тестовете за този модул според Odoo 15 best practices:

```bash
# Изпълнете всички тестове за модула
python odoo-bin -c /path/to/odoo.conf -d test_db -i hr_attendance_late --test-enable --stop-after-init

# Изпълнете само post-install тестовете
python odoo-bin -c /path/to/odoo.conf -d test_db --test-enable --test-tags=hr_attendance_late --stop-after-init

# Изпълнете конкретен тест клас
python odoo-bin -c /path/to/odoo.conf -d test_db --test-enable --test-tags=/hr_attendance_late:TestAttendanceCalculationSimple --stop-after-init
```

## Покритие на тестовете

Тестовете покриват следните случаи:

### 1. test_normal_attendance
- Нормално работно време (8:00-17:00)
- Проверява правилното изчисление на теоретично и действително работно време

### 2. test_missing_checkout_within_max_time
- Липсващ check-out в рамките на max_time_in_zone
- Използва текущото време за изчисление

### 3. test_missing_checkout_exceeds_max_time
- Липсващ check-out след изтичане на max_time_in_zone
- Автоматично затваря с auto_close_time_for_zone часове

### 4. test_late_arrival_within_tolerance
- Закъснение в рамките на толеранса на отдела
- Игнорира малки закъснения (под 5 минути)

### 5. test_multi_day_attendance
- Нощна смяна през два дни
- Правилно разделя часовете между дните

### 6. test_overtime_calculation
- Извънреден труд след редовното работно време
- Изчислява правилно overtime часовете

### 7. test_out_of_order_event_handling
- Автоматично преизчисление при промяна на attendance
- Симулира out-of-order RFID събития

### 8. test_error_handling_with_invalid_data
- Обработка на грешки без спиране на процеса
- Логва грешки и продължава с другите служители

## Важни бележки

1. Тестовете използват `freezegun` за контрол на времето
2. Създават се тестови зони с конфигурация за auto-close
3. Тестват се всички основни edge cases от реалната среда
4. Проверява се интеграцията с department tolerance настройките

## Добавяне на нови тестове

При добавяне на нови функционалности, създайте съответни тестове в `test_attendance_calculation.py` следвайки същата структура.