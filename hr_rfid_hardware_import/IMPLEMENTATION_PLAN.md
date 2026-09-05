# План: hr_rfid_hardware_import - опис на работеща система (read-only) и безопасен внос

## Context

Инсталацията на polimex-rfid сета върви "отгоре надолу": подава се хардуерът,
модулите го инициализират (нулират контролерите), после се настройват групи за
достъп, права, хора. Собственикът иска модул, който прави ОБРАТНОТО: заварва
работеща система (контролери с карти и права, настроени от друга система или на
ръка), описва я БЕЗ да я променя, и предлага внос на хората, групите за достъп и
накрая на самия хардуер, така че реалният хардуер да не загуби работоспособност.
Модулът е добавка в менютата, както импортите от стари системи.

Осемте точки от заданието (дословно, 2026-09-03):
1. автоматична детекция на webstack модули + ръчно добавяне на IP за модули зад рутери
2. списък на всички контролери от всеки модул със състоянието им: настройки +
   всички карти с правата им (вкл. security флагове за СОТ и APB); вендинг се изключва
3. целта е опис на работеща система без промяна
4. csv/excel с 2 колони (име, номер на карта) -> обвързване на карти с имена
5. анализ на картите и правилата -> потенциални групи за достъп + коя карта в коя
6. без имена -> служебни имена
7. предложение за внос на имена+карти като служители и/или партньори (избор) +
   създаване на групите за достъп
8. накрая - внос на целия хардуер, без нулиране; всяка стъпка с възможност за
   пропускане; командите към контролерите са СТРОГО само за четене

Ограничения от правилата: домейнът на сесията е само този модул (hr_rfid не се
пипа); универсален модул; никакви клиентски данни в repo; мигрираните данни не
минават през чужд код (`no_hardware_commands`, нула команди за запис в E2E);
wire детайлите на протокола (частна ИС) не влизат в README/llms/help текстове.

## Решения на собственика (2026-09-03/04, AskUserQuestion, 12 въпроса)

| # | Въпрос | Решение |
|---|---|---|
| 1 | Име | `hr_rfid_hardware_import`; меню „Внос от работеща система" |
| 2 | Еднакво име на два реда във файла | сливане по нормализирано име + списък „Проверете" с бутон „Раздели" преди вноса |
| 3 | Два контролера с различно съдържание в един TS слот | вносът на графици спира, докато операторът не избере контролер-източник за всеки конфликтен слот; разликата за останалите контролери влиза в отчета |
| 4 | Стъпка 8 | записи в Odoo без нито една команда + ОТДЕЛЕН изричен бутон „Насочи модула към този сървър" (преизползва `hr.rfid.webstack.action_set_webstack_settings`, единственият запис по устройство) |
| 5 | Дълги четения | фонов cron worker с прогрес, възобновяване по контролер (шаблон hr_rfid_odoo_import) |
| 6 | Контролери извън семейството за достъп (пожарен, температурен, газ, релеен, IO) | ВНАСЯТ СЕ като контролери БЕЗ карти; вендинг (hw 16) се изключва изцяло |
| 7 | Групи | „минимален брой": право = (врата, график, СОТ); права с ЕДНАКЪВ набор от карти = една група („тези врати винаги вървят заедно"); картата е в толкова групи, колкото набора докосва; групите не споделят права; детерминирано |
| 8 | Служебен собственик | контакт (партньор) по подразбиране; смяна за целия опис и по ред |
| 9 | Човек с карти с различни права (Odoo дава обединението) | предупреждение в „Проверете" с точните допълнителни права; бутон „Раздели"; без действие се внася обединението |
| 10 | Асиметрии (само входен четец; различен график на двата четеца) | внася се като право на вратата с графика на входния четец + отбелязване в отчета и в прегледа |
| 11 | Odoo вече има непразен фирмен график N, различен от контролерите | ЖЕЛЯЗОТО ПЕЧЕЛИ: фирменият график се презаписва (без питане, ако контролерите са единодушни); отчетът изброява съществуващите контролери на фирмата, които вече се разминават |
| 12 | Темпо на четене | БЕЗ изкуствени паузи между страниците; единственото темпериране са повторните опити по e-код (20/23/12/24) |

## Prior-art (2026-09-03)

- Локално: три импорт модула (andromeda, old_cloud, odoo_import) - шаблон за
  меню/съветник/ledger/worker; `hr_rfid/models/hr_rfid_webstack_discovery.py` вече
  открива webstack-ове (но после ПИШЕ по тях - не се преизползва setup_modules).
- odoo-code-search.com: недостъпен (Odoo database manager без база, 404 на
  /ocs/search) - дефект на външния сайт.
- GitHub: `gh search repos rfid --owner OCA` -> 0; `"access control" --owner OCA`
  -> 0; `gh search code "hr.rfid.webstack"` -> само polimex/polimex-rfid.
- MODULE_INDEX + grep в custom-addons: нищо не чете карти обратно от контролер;
  най-близки шаблони: `hr_rfid_webstack_discovery` (scan-and-adopt UX),
  `polimex_ip_cam/cctv_camera_discovery_wizard.py` (status new/known + тестов seam),
  `hr_rfid_odoo_import` (ledger, run, cron worker, showcase демо, tour).
  Извод: собствен модул в сета, без външна зависимост.


- **LAN discovery**: UDP broadcast 255.255.255.255:30303, payload `Discovery:`;
  отговор `\r\n` редове: hostname, MAC, hw, fw, сериен, bridge порт
  HTTP fallback `GET /discovery.json` или `GET /config.json`.
  `GET /config.json` (convertor, sdk.sdkVersion/sdkHardware/devFound, sdkSettings.
  Server_URL - само за показване), `GET /sdk/details.json` (devFound,
  maxDevInList=64), `GET /sdk/status.json?dev=N` (devID, devHardware, devSoftware,
  devSerial, isOnline), `POST /sdk/cmd.json` (`{"cmd":{"id":адрес,"c":опкод,"d":данни}}`
  -> `d`, `e`). Auth опционален (`enable_sdk_password_require`). НИКОГА: `?scan=1`,
  `/sdk/out.json`, `/protect/*`, `/sdk/setkey.json`. КАПАНИ: `isOnline:0` не значи
  офлайн (проверка с F0); грешен HTTP метод връща 404, не 405; пасивен gateway може
  да върне отговор на ПРЕДИШНА команда - винаги сверка `id` + `c` (skew guard).
- **READ allowlist**: F0 F1 F2 F3 F4 F5 F6 F7 F8 F9 FB FC FF B3 + B0 с данни `01`.
  Забранени: всички D* (DC 0303 трие карти, 0404 събития, 0101 фабрични; D0 адрес;
  D1/D2 карти; D3-D9/DD/DF записи; DB отваря релета; DA мести event пойнтера),
  BF/C1, B0/B1/B2 write форми, FA (безопасна, но безсмислена без DA - не се праща).
- **Картова таблица**: F2 форма 1 (`0000000000`) = брой; форма 2 = позиция (5 B
  per-digit BCD, 1-базирана) + брой (1 B, страница 5 = READ_CARDS_BLOCK_SIZE); запис
  19 B (iCON110/130/130T/50) или 20 B (iCON115/180: последният байт = СОТ bitmap
  Z1-Z4); [0:10] номер per-digit BCD, [10:14] PIN, [14..17] TS за четци 1-4 (0 =
  винаги), [18] rights bit0-3 четци, bit5 apb2, bit6 apb1 (runtime). record_size от
  hw_code/alarm_lines на F0, не от дължината. Relay hw31 = 34 B (друг формат, извън
  обхвата), temp = 36 (сензори).
- **Кодове e**: 0 OK; 14 unknown_command = capability gap; 4 wrong_value = gap само
  при hw31; 20 no_response, 23 bridge_active, 12 busy, 24 internal - повторни опити.
- **HW**: 6 iCON110, 9 iCON130 Turniket, 10 iCON180, 11 iCON115, 12 iCON50, 13/14
  hotel, 16 ВЕНДИНГ (стари Smart Vend билдове рапортуват hw 10 - риск J1), 17
  iCON130, 18 Fire, 22/23/24 temp, 25 iGas, 26 Power, 30-32 Relay, 34/35 IO, 40-49
  MFReader, 50 iMotor. Лимити: карти 1526/9727/15870/7679/1536; 15 графика (слот 0 =
  винаги, F3 с 0 чете конфиг страницата - забранено на ниво allowlist); 64
  контролера на webstack; бус ~50 ms/картов запис.
  `backup()` (:114-256): F0 -> F5, F6, FB, F8, FC, FF, F9 "00", B0 "01" (alarm_lines>0),
  F3 1..ts_count, F4 1..8, F7, B3, F2 count, F2 страници.
- Режим -> врати (= логиката на `parse_f0_response`): mode1/3: врата1=[R1,R2];
  mode2+4 четеца: (R1,R2)(R3,R4); mode2+2 или mode4: (R1)(R2); mode3 добавя
  врата2=[R3], врата3=[R4]; mode4 добавя врата3=[R3], врата4=[R4].

## Находки от hr_rfid (v19.0.2.33.0; пътища спрямо `polimex/hr_rfid/`)

- **Нулирането** е в `models/hr_rfid_command.py:808 parse_f0_response()`:
  `ctrl_already_existed` = ctrl намерен по `serial_number` в СЪЩИЯ webstack
  (:850-857); само при False (:1061-1074) се редят D7, DC 0303, DC 0404, F6/F9/FB/FF/
  B3, FC. Нито един контекстен флаг не пази блока. => Безопасен път: ctrl се създава
  с ПРЕДВАРИТЕЛНО попълнени `serial_number`, `webstack_id`, `mode`, после уловеният F0
  се подава през `parse_f0_response` -> existing branch -> без DC/D7; вратите и
  четците се строят от ядрото; `mode` предварително равен => `change_io_table` (D9,
  :1050-1055) не се вика. За hw 22 ядрото пак реди F2 + B1 '01' (:1076-1078) -
  четящи, допустими.
- **Командите не тръгват**, докато webstack-ът е `active=False`:
  `hr_rfid_command.py:765-768` (`direct_execute` само при active и без WS),
  `hr_rfid_ctrl.py:1018-1019` `_base_command`. => Вносът създава модула неактивен;
  „Насочи" + „Активирай" са отделни бутони.
- **Капани при запис** (проверени 2026-09-04): `hr_rfid_ctrl.py:800-803` -
  `alarm_sensor_events` в write => B0 WRITE независимо от контекста (затова се подава
  при CREATE); `:808/:818/:820` `from_controller` пази D5/DF/DD; `hr_rfid_webstack.py:
  732-745` - смяна на `tz` при write => D7 към всички контролери (tz се дава при
  create); `hr_rfid_ctrl.py:1319-1325` `write_ts_id` под `no_hardware_commands` НЕ
  добавя `controller_ids` => вносът ги добавя ръчно.
- **`no_hardware_commands`** се чете в `hr_rfid_door.py:548` (DE), `:846`/`:857`
  (D1), `hr_rfid_ctrl.py:1320`/`:1328` (D3), `hr_department.py:50`,
  `hr_employee.py:296`. Каноничен пакет `IMPORT_CONTEXT`:
  `hr_rfid_odoo_import/models/importers/base_importer.py:38-46` (копира се локално).
- **Чисти парсери за преизползване**: `_parse_f0_cmd` (:792-806), `bytes_to_num`,
  `str_hex_to_array`, `HW_TYPES`, `READ_CARDS_BLOCK_SIZE` (`controllers/polimex.py`),
  `get_ctrl_model_name`, класификатори `hr_rfid_ctrl.py:738-766`.
- F2 парсерът на ядрото (`hr_rfid_webstack.py:1251-1297`) декодира само брояча и
  температурните сензори - картовият запис се декодира в новия модул.
- **Модели за внос**: webstack (serial, last_ip, hw_version, behind_nat,
  module_username/password, active default False; `key` делегиран към
  `polimex.ws.endpoint`), ctrl, door (number, apb_mode), reader (number,
  reader_type, mode), time.schedule (16 на фирма, number 0-15, `ts_data` = 260 hex =
  точно формата на F3 отговора и на D3), card (number w34/w34s, `internal_number`,
  точно един собственик), card.door.rel (`alarm_right`), access.group (+ door.rel с
  time_schedule_id/alarm_rights; write() забранен - unlink+create; employee.rel /
  contact.rel).
- Менюта: родител `hr_rfid.hr_rfid_root_menu_hardware_manager`, заети seq
  7-90 -> нов seq 95, група `base.group_system`. Тестове: `tests/common.py`
  `RFIDAppCase`, F0 фикстури `:203-221`; `_registry_readonly_enabled = False`.
- base_import (ядро): `base_import.import._read_file(options)` диспечира по
  mimetype/разширение към `_read_csv/_read_xlsx/_read_xls/_read_ods`
  (`odoo/addons/base_import/models/base_import.py:374-601`) - файлът не се парсва
  на ръка.

## Архитектура (препоръчан подход)

Персистентен „опис" (run) с машина на състоянията и notebook страници; трите
дълги фази (откриване, четене, внос) вървят в cron worker; малки transient
съветници за ръчен IP, файл с имена, опции за внос, сливане на групи. Транспортът
е собствен тънък клиент с allowlist на ниво изпращач (hr_rfid's
`_execute_direct_cmd` иска запис на модул, а модулът не бива да се създава преди
операторът да реши). Вносът пише изцяло под `IMPORT_CONTEXT` и минава през
existing-branch на `parse_f0_response`.

### A. Файлово дърво `custom-addons/polimex/hr_rfid_hardware_import/`

```
__manifest__.py            depends ['hr_rfid','base_import']; version 19.0.1.0.0; AGPL-3; HR
README.rst                 8-те стъпки, какво никога не прави (без wire детайли)
docs/llms.txt, docs/llms-full.md   шаблон от hr_rfid_odoo_import/docs
i18n/*.pot, bg.po
helpers/allowlist.py       READ_OPCODES + ForbiddenOpcode + индексни гардове F3(1..15)/F4(1..8)
helpers/transport.py       HardwareClient (requests, skew guard, retry по e), UdpDiscovery
helpers/codecs.py          всички декодери (card record, F3->ts_data, F4, F5, F6, F9, FB, FC,
                           FF, B0, B3, F7), reader->door и zone->door карти, family, record_size
helpers/fake_transport.py  FakeTransport за тестове/tour/демо (скриптирани отговори, allowlist)
models/hw_import_run.py    hr.rfid.hw.import.run (state machine, worker, фази)
models/hw_import_module.py hr.rfid.hw.import.module
models/hw_import_ctrl.py   hr.rfid.hw.import.ctrl
models/hw_import_card.py   hr.rfid.hw.import.card + .card.record
models/hw_import_ts.py     hr.rfid.hw.import.ts + .ts.slot
models/hw_import_group.py  hr.rfid.hw.import.group + .group.right
models/hw_import_person.py hr.rfid.hw.import.person
models/hw_import_name.py   hr.rfid.hw.import.name
models/hw_import_issue.py  hr.rfid.hw.import.issue
models/hw_import_cmd_log.py hr.rfid.hw.import.cmd.log (@api.autovacuum)
models/reader.py           SurveyReader - последователността на четене с курсори (plain class)
models/analyser.py         SurveyAnalyser - права, групи, хора, TS конфликти (plain class)
models/importer.py         HardwareImporter - вносът (ledger, IMPORT_CONTEXT, F0 трик)
wizards/hw_import_add_ip_wiz.py, hw_import_names_wiz.py, hw_import_options_wiz.py,
        hw_import_group_merge_wiz.py, hw_import_wizard_views.xml
views/hw_import_*_views.xml (run, module, ctrl, card, person, group, ts, issue, cmd_log)
security/ir.model.access.csv (всички -> base.group_system), hw_import_security.xml
        (record rules по company_id на run-а; децата през run_id.company_id)
data/ir_cron.xml           ir_cron_hw_import_run: активен, noupdate="1", model._cron_process()
demo/hr_rfid_hardware_import_demo_showcase.xml   ЕДИН завършен опис, без I/O
static/description/icon.png
static/tests/tours/hw_import_survey_tour.js, hw_import_names_tour.js, hw_import_groups_tour.js
tests/common.py + test_allowlist, test_transport, test_codecs, test_discovery,
      test_read_resume, test_analysis_groups, test_names_file, test_ts_conflicts,
      test_import_end_to_end, test_import_mixed_hardware, test_rerun_idempotent,
      test_point_module, test_multi_company, test_tours
```

Конвенции: `help=` на всяко поле; `index=True` на всеки търсен M2O; `models.Constraint`;
`self.env._()`; `@api.model_create_multi`; `company_id` само на run-а.

### B. Модели (ключови полета)

- **run** (`mail.thread`, `_order='create_date desc'`): name (compute store),
  company_id (required, index), user_id, state [draft, discovering, reading,
  analysing, naming, grouping, importing, done, failed] (tracking), discovery_broadcast,
  discovery_timeout, O2M към всички редове, names_file (attachment) + names_file_name,
  placeholder_owner_type (employee/contact, default contact), default_department_id
  (задължителен щом има служител), import_hardware/import_schedules/import_people/
  import_cards/import_groups (Boolean default True - всяка стъпка е пропускаема),
  current_phase, done_count, total_count, progress (compute), phase_done_json,
  read_cursor_json, discovered_at/read_at/analysed_at/imported_at, last_error,
  броячи compute (module/ctrl/card/person/group/blocker_count), has_blockers.
  Клас-атрибут `_transport_factory = None` (тестов seam). Константи PASS_SECONDS=5,
  STALLED_MINUTES=30 (с обосновката от import_run.py:26-36).
  Методи: action_discover, action_add_module, action_read, action_refresh (без
  записи), action_skip_names, action_to_grouping, action_back_to_naming,
  action_open_import_options, action_start_import, action_download_report,
  action_point_modules, _wake_the_worker, _cron_process, _abandon_stalled_runs
  (чисти и паролите), _process_pass, _pass_discover/_pass_read/_pass_analyse/
  _pass_import, _save_progress, _finish, _log_issue.
  Преходи: draft -(discover)-> discovering -> draft (модулите се преглеждат) -(read)->
  reading -> analysing -> naming -(файл/пропусни)-> grouping -(import)-> importing
  -> done; всяка грешка в worker-а -> failed (last_error).
- **module**: run_id, source (broadcast/manual), ip, port (80), hostname, mac,
  serial (index), hw_version, fw_version, bridge_port, dev_found, server_url (само
  показване), status (new/known/unreachable), existing_webstack_id, include (new ->
  True, known -> False), module_username/module_password (groups=base.group_system,
  чистят се при _finish), config_json (без ключове/пароли), read_state, read_error,
  ctrl_ids, webstack_id (създаден/приет), pointed_at, pointed_by_id.
  Constraints: UNIQUE(run_id, ip, port); serial уникален в run при непразен.
  Методи: action_probe, action_point_to_server, action_enable_module.
- **ctrl**: run_id, module_id, address, dev_index, name (compute store), hw_code,
  hw_name, family (compute store: access/vending/relay/temperature/fire/gas/power/
  io/reader/motor/hotel/unknown), serial (index), sw_version, mode, external_db,
  dual_person, interlocking, relay_time_factor, readers, inputs, outputs,
  time_schedules, io_table_lines, alarm_lines, max_cards, max_events, record_size;
  сурови hex (Char/Text): f0_hex, f5_hex, f6_hex, f8_hex, f9_hex, fb_hex, fc_hex,
  ff_hex, b0_hex, b3_hex, f7_hex; декодирани JSON: reader_modes_json, io_table_hex
  (448 знака), input_mask, output_relay_mask, apb_bitmap, out_ts_json,
  alarm_setup_json, status_json, holidays_json, clock_read, clock_drift_seconds,
  gaps_json; четене: card_count_device, cards_read, read_cursor (-1 = готово),
  read_state (pending/config/cards/done/failed/skipped), read_error, include
  (вендинг -> False, readonly); внос: existing_ctrl_id (конфликт), ctrl_rec_id,
  imported_without_doors, door_map_json, zone_map_json. UNIQUE(module_id, address).
- **card** (логическа, по номер): run_id, number (10 знака = `internal_number`),
  number_display (по card_input_type на фирмата), pin, pin_mismatch, record_ids,
  door_rights_json, rights_key, apb_bits_json (записва се, НЕ се внася), anomaly
  (none/bad_bcd/reader_ts_mismatch/partial_reader/no_rights/pin_mismatch),
  person_id, group_ids (M2M), existing_card_id, card_rec_id, include.
  UNIQUE(run_id, number). **card.record**: card_id, ctrl_id, position, raw_hex, pin,
  ts_r1..ts_r4, rights, apb1, apb2, alarm_bits, anomaly. UNIQUE(ctrl_id, card_id).
- **ts** (по контролер и слот): run_id, ctrl_id, number 1..15, raw_hex (260 = бъдещ
  ts_data), week_fingerprint (sha1 на байтове 1..128), holiday_ref, is_empty,
  summary („Пон-Пет 08:00-18:00"), slot_id. UNIQUE(ctrl_id, number).
  **ts.slot** (по run и слот): number, ts_ids, variant_count (compute store),
  existing_ts_id (фирмен слот N), existing_is_empty, existing_differs, source_ctrl_id
  (изборът), state (ok/conflict/resolved compute store), decision_note.
  Правило (решения 3 + 11): variant_count > 1 -> conflict до избор на source_ctrl_id;
  variant_count == 1 -> ok, желязото печели над фирмения график (existing_differs
  само се докладва: списък на съществуващи контролери на фирмата със слота).
- **group**: run_id, sequence, name (Char 32 - лимитът на hr_rfid AG), holder_key
  (sha1 на сортираните номера карти), card_ids (M2M), card_count, right_ids,
  door_count, include, merged_from_json, access_group_id. UNIQUE(run_id, holder_key).
  **group.right**: group_id, run_id, ctrl_id, door_number, ts_number, alarm,
  door_rec_id. UNIQUE(run_id, ctrl_id, door_number, ts_number, alarm) - „групите не
  споделят права" е в базата.
- **person**: run_id, name, name_key (normalised), source (file/placeholder),
  owner_type, card_ids, card_count, pin, pin_conflict, rights_differ (решение 9 -
  предупреждение), ts_conflict (същата врата с различен график между картите на
  човека -> `check_for_ts_inconsistencies` би вдигнал -> blocker), review_state
  (ok/review/blocked), include, employee_id, partner_id. action_split,
  action_merge_into.
- **name**: run_id, row_number, name_raw, number_raw, number_norm, card_id,
  person_id, status (matched/unmatched/duplicate/invalid), note.
- **issue**: run_id, kind (conflict_webstack/conflict_ctrl/conflict_card/ts_conflict/
  pin_conflict/rights_union/anomaly/gap/decision/report/warning), severity (info/
  warning/blocker), message, незадължителни M2O към module/ctrl/card/person/slot/
  group, target_model, target_id, resolution (none/link/skip/accept), resolved.
- **cmd.log**: run_id, module_id, address, opcode (index), data_sent, e_code,
  duration_ms, response_hex, skewed, attempt, note. `@api.autovacuum _gc_cmd_logs`
  (GC_DAYS=90, GC_LIMIT=5000 на минаване, връща (done, has_more)).

### C. Транспорт (`helpers/`, чист Python)

- `allowlist.check_allowed(opcode, data)`: READ_OPCODES = {F0,F1,F2,F3,F4,F5,F6,F7,
  F8,F9,FB,FC,FF,B3}; B0 само с data '01'; F3 индекс 1..15; F4 1..8; всичко друго ->
  `ForbiddenOpcode` ПРЕДИ мрежа. HTTP пътища също allowlist: `/config.json`,
  `/sdk/details.json`, `/sdk/status.json?dev=N`, `POST /sdk/cmd.json`,
  `/discovery.json`.
- `HardwareClient(host, port=80, auth=None, on_log)`: get_config/get_details/
  get_status (timeout (3,10)); `cmd(address, opcode, data)` -> Reply(address, opcode,
  e, data_hex, duration_ms, attempts, skewed): allowlist -> POST -> skew guard
  (`id`==адрес и `c`==опкод, до 8 повторения през 0.5 s) -> политика по e: 0 ok; 20
  повтори 3x (0.5/1/2 s) после ReadFailed; 23 повтори 6x през 5 s; 24 2x; 12 3x през
  2 s; 14 -> CapabilityGap; 4 -> CapabilityGap само при relay=True; друго ReadFailed.
  Без изкуствени паузи (решение 12). Всеки опит -> on_log -> cmd.log ред.
- `UdpDiscovery.broadcast(timeout)` (огледало на `_discover_ws`, но пази ВСИЧКИ
  отговори - регистрираните стават `known`) и `unicast(ip)` с fallback към
  `get_config()` (serial = `convertor`, hw = `sdk.sdkHardware`, fw = `sdkVersion`).
- Seam: клас-атрибут `run._transport_factory` (не контекстен ключ - кронът работи в
  нов environment). `FakeTransport(script)` отговаря на discovery/config/status/cmd
  от речник, записва всяко повикване, налага allowlist, може да инжектира skew и
  e=20.

### D. Кодеци (`helpers/codecs.py`, чисти функции)

F0 през `_parse_f0_cmd` + readers = hex[30:32] + mode byte бити (:813-818);
`f0_would_pass(dec, hw)` повтаря проверките на parse_f0_response (:824-835, :934-936).
`family_of(hw)`, `record_size_of(hw, alarm_lines)` (19/20 достъп; 34 relay; 36 temp;
None -> F2 не се праща). `decode_card_record`/`decode_cards_page` (терминатор =
all-zero/all-FF запис; дължина не кратна на record_size -> PageShapeError).
`encode_f2_count()`, `encode_f2_page(position, count)` (както `hr_rfid_ctrl.py:1154-1172`).
F3 -> `ts_data = reply_hex.upper()` дословно (същата форма като DEFAULT_TS_LINE),
`week_fingerprint`, `is_empty`, summary. F4, F5, F6 (mode_n/mode_ts/ts), F9 (100.1
цяла таблица; 10.3 по редове; дължина = io_table_lines*16 иначе gap), FB, FC, FF,
B0 '01' (полярност както `hr_rfid_ctrl.py:986-991`; 1-байтов отговор = defaults),
B3 (копие на `hr_rfid_webstack.py:1376-1412`), F7. `reader_door_map(hw, mode,
readers)` и `zone_door_map(alarm_lines, mode)` = точно `parse_f0_response`
(:974-1016) и `_setup_alarm_lines` (`hr_rfid_ctrl.py:851-865`); test_codecs ги
сверява срещу реално създадените от ядрото врати/четци/зони за всяка F0 фикстура.

### E. Анализ (`models/analyser.py`)

1. Запис -> права по врата: за всяка врата от `reader_door_map`: битовете на
   нейните четци; никой -> няма право; част -> право + anomaly `partial_reader`
   (решение 10); ts = на най-малкия четец с бит; различни ts -> `reader_ts_mismatch`
   (решение 10); alarm = битове на зоните на вратата в alarm байта. APB битовете ->
   `apb_bits_json` (само запис).
2. Логическа карта по номер; PIN = общият ненулев; различни -> pin_mismatch.
3. Групи (решение 7): R = различните права (ctrl_row, door, ts, alarm); holders(r)
   = frozenset(card ids); дял по holders -> група с rights(H) и members H.
   Подредба (-|H|, -|rights|, min ключ); имена „Група за достъп N - M врати" (<=32).
4. TS слотове: вариантите по fingerprint; правилата от B (решения 3 и 11).
5. Хора: placeholder за всяка карта („Карта <number_display>", тип по run-а);
   при файл - слети по name_key (решение 2), rights_differ -> warning + „Раздели"
   (решение 9), ts_conflict -> blocker, PIN конфликт -> warning, без PIN.
6. Конфликти с existing записи (докладват се, не се решават): webstack по serial;
   ctrl по serial_number САМО (parse_f0_response търси само по serial и UNLINK-ва
   новия при друг webstack) -> при конфликт: skip/link, без fallback; card по
   internal_number в компанията. blocker_count пази бутона „Внос".

### F. Имена (`wizards/hw_import_names_wiz.py`)

`base_import.import.create({res_model, file, file_name, file_type})` ->
`_read_file({'quoting':'"','separator':'','encoding':'','sheet':''})` -> редове;
transient-ът се трие; файлът остава на run-а. Колона с предимно цифри = номер,
другата = име; първи ред с нецифров номер = заглавие; < 2 колони -> UserError с реда.
Нормализация на номера (`normalise_card_number`): само цифри; <=10 -> ляво
допълване с нули (както `check_and_fix_card_numer`); w34s фирма -> преобразуване
по `_compute_internal_number` (`hr_rfid_card.py:153-166`). Съвпадение САМО по
номер. Статуси matched/unmatched/duplicate/invalid. Повторно качване рестартира
стъпката (съветникът го казва).

### G. Внос (`models/importer.py`, worker фаза, всяка стъпка е resumable единица)

Контекст: локален `IMPORT_CONTEXT` (6-те ключа от base_importer.py:38-46) +
`from_controller=True` където hr_rfid го чете. Ledger: `ir.model.data`, module
`__import__`, име `rfid_import_hw_{ws_serial}_{model_prefix}_{ref}`;
already_imported / link_existing / adopt_existing по образеца на base_importer.
Ред (всяка стъпка пазена от отметката си; пропусната -> `report` issue):
- G1 Графици: за всеки слот (ok/resolved): `existing_ts_id.with_context(IMPORT_CONTEXT)
  .write({'ts_data': chosen.raw_hex})` (TS няма write hook) + `controller_ids +=`
  всички внесени контролери със СЪЩИЯ fingerprint (за да не се пуска D3 по-късно);
  различаващите се -> report ред.
- G2 Модули: `hr.rfid.webstack` create с serial, hw_version, version, behind_nat=
  False, last_ip, **active=False**, available='a', company_id, **tz при create**
  (write на tz => D7), module_username/password.
- G3 Контролери: (1) `f0_would_pass` + без serial конфликт; (2) `hr.rfid.ctrl`
  create (IMPORT_CONTEXT + from_controller) с ПРЕДВАРИТЕЛНО serial_number,
  webstack_id, ctrl_id, name, hw_version, sw_version, **mode**, io_table (при вярна
  дължина), **alarm_lines_setup + alarm_sensor_events при create** (write => B0
  WRITE), inputs_mask, B3 полета, last_f0_read; (3) `hr.rfid.command` create
  {cmd 'F0', status 'Success'} (инертен: неактивен модул) и
  `cmd.parse_f0_response({'response': {'id', 'c':'F0', 'e':0, 'd': f0_hex}})` ->
  existing branch: ядрото строи вратите/четците, без DC/D7/D9; (4) fallback (решение
  6): ако F0 не минава проверките - ctrl само от декодирания F0, без врати/четци,
  `imported_without_doors=True` + report; (5) огледала през хуковете на ядрото:
  `_setup_alarm_lines()` + line.write(from_controller), reader.write({'mode',
  'no_d6_cmd': True}), `process_input_masks`, output_ts_ids write (from_controller),
  door.write({'apb_mode'}) под IMPORT_CONTEXT; (6) вендинг никога.
- G4 Хора: employee (IMPORT_CONTEXT, department = default, pin ако != '0000') или
  partner (company_type person, type contact). Преди членства: отделът получава
  всички внесени групи в `hr_rfid_allowed_access_groups` (иначе `check_access_group`
  вдига).
- G5 Карти: `hr.rfid.card` create (number_display, card_input_type на фирмата,
  собственик).
- G6 Групи: `hr.rfid.access.group` + `access.group.door.rel` create директно
  (time_schedule_id = фирмен слот N, alarm_rights) + членства ПОСЛЕДНИ
  (employee.rel/contact.rel) -> ядрото извежда card.door.rel под
  `no_hardware_commands` -> нула D1. Базата = желязото.
- G7 Отчет: report issues + `action_download_report` (текстов attachment);
  `_finish('done')` чисти паролите.
- G8 „Насочи модула към този сървър" (единственият запис по устройство, отделен
  бутон с потвърждение): `webstack_id.action_set_webstack_settings()` (ядрото,
  непроменено); после отделен бутон „Активирай модула в тази система" (`active=True`
  - оттук нататък hr_rfid работи нормално с него).
Идемпотентност: всяка стъпка пита ledger-а; повторен опис върху същия обект не
създава нищо и докладва „вече е налице".

### H. UX

Run форма: statusbar; header бутони по състояние (draft: „Намери модулите в мрежата"
primary, „Добави модул по адрес", „Прочети контролерите" primary при модули;
worker: „Провери отново" + progressbar + current_phase; naming: „Качи файл с
имена", „Пропусни имената", „Към групите" primary; grouping: „Назад", „Слей
избраните групи", „Внос..." primary, забранен с tooltip при blockers; done: „Насочи
модула", „Изтегли отчета"). Банери: info (worker), warning (blockers), success
(„Нищо не е изпратено към контролерите. За да предадете модула на тази система
натиснете ..."). Notebook: Модули, Контролери, Карти, Хора (филтри „За преглед",
„Блокирани", „Служебни"), Групи (inline редакция name/include + права), Графици
(варианти + избор на източник), Проблеми (група по вид, resolution), Лог.
Empty state на action-а (2 абзаца). Меню: `hw_import_menu` „Внос от работеща
система", parent hardware manager, seq 95, groups base.group_system. Help текстове
без опкоди/байтове; wire детайлите само в helpers/ докстринги и тестове.

### I. Process narratives (мин. брой backend E2E + tour-ове)

1. Опис на LAN обект от край до край: откриване -> четене -> анализ -> без файл ->
   внос; нула команди за запис (`hr.rfid.command` с cmd D*/DB/DC или B0/B1 с данни
   '00..' == 0), опкодите в лога са подмножество на allowlist-а, card.door.rel-ите
   = правата на желязото, модулът неактивен. (`test_import_end_to_end`)
2. Модул зад рутер: ръчен IP -> проба -> new/known/unreachable -> четене.
   (`test_discovery`)
3. Файл с имена CSV и XLSX: matched/unmatched/duplicate/invalid, w34s
   преобразуване, сливане в един човек, разделяне. (`test_names_file`)
4. Без имена: служебни собственици „Карта N" като контакти; един ред сменен на
   служител изисква отдел. (`test_names_file`)
5. Конфликт на графици блокира до избор на източник; желязото печели над Odoo
   графика; отчетни редове. (`test_ts_conflicts`)
6. Повторен опис: без дубликати; конфликти webstack/ctrl/card докладвани с
   link/skip. (`test_rerun_idempotent`)
7. Смесен хардуер: вендинг изключен (F0 само, без F2 в лога), relay/fire/temp без
   карти, fallback без врати, e=14 като gap. (`test_import_mixed_hardware`)
8. Насочване на модула: `requests` мокнат; ядрото вика само `/protect/uart/conf`,
   `/protect/config.htm` (+reboot за 10.3); pointed_at; без hr.rfid.command.
   (`test_point_module`)
9. Прекъснато четене се възобновява: PASS_SECONDS=0, няколко `_cron_process`,
   курсорът по контролер напредва; застоял run се изоставя след 30 мин.
   (`test_read_resume`)
10. Операторът слива две групи: предупреждението изброява допълнителните права;
    слятата група се внася веднъж. (`test_analysis_groups`)
Плюс отрицателни: `test_allowlist` (D1, DA, DC, B0 '00', B1 '00', F3 '00', F4 '09'
вдигат преди fake-а да види нещо), `test_transport` (skew, e=20 retry, e=23),
`test_codecs` (картите на четци/зони = реалните врати на ядрото за всяка F0
фикстура; ts_data round-trip през `_get_interval_from_day_tuple`),
`test_multi_company`. Tour-ове (3, с `run: "edit"/"click"`, селектори по клас,
край `body:not(:has(.modal))`): survey (ново -> „Добави модул по адрес" -> IP ->
ред със status badge), names (run в naming -> съветник -> „За преглед" -> Раздели),
groups (run в grouping -> inline име -> съветник за сливане -> отказ).
Демо: един run в `done` (инертен за крона), 1 модул, 3 контролера (180, 110, fire без
карти), 6 карти, 3 души (един слят, един служебен), 2 групи, 2 слота, issues, 10 лог
реда с измислени hex; JSON колоните в точния вид на кода.

### J. Приети рискове / бележки

- J1 Стари Smart Vend с hw 10: показва се sw_version + warning при вендинг профил;
  операторът маха отметката.
- J2 B0 на iCON180 < v7.42 -> e=14 -> gap; зоните с defaults + report.
- J3 Контролер с чужд serial в друг webstack/фирма -> conflict (skip/link), без fallback.
- J4 Relay (hw 30-32): без карти (34 B формат извън обхвата); F3 e=4 -> gap.
- J5 Неактивен модул + чакащи четящи команди на ядрото за hw 22 - изпълняват се
  след „Активирай"; документирано.
- J6 Суровите hex остават на редовете на описа (доказателство); логът се чисти
  след 90 дни.
- J7 Съществуващи контролери на фирмата, чиито слотове вече се разминават с
  презаписания фирмен график (решение 11) - изброени в отчета; hr_rfid ще ги
  пренастрои при следваща редакция на графика.

## Ред на изпълнение (odoo-dev-workflow, стъпка по стъпка, с обявяване)

0. Папка в сета (указание на собственика „всичко събирай в нова папка в модулния
   сет"): `custom-addons/polimex/hr_rfid_hardware_import/` + `IMPLEMENTATION_PLAN.md`
   (този план, без локалните пътища към частния spec repo и без нищо клиентско;
   wire детайлите остават на нивото, на което hr_rfid вече ги носи в кода) +
   symlink в `odoo19/addons/`. Прогресът по стъпките се води в същия файл.
1. Скилове: заредени brainstorming, odoo-dev-workflow, odoo-wizard-guide,
   odoo-ux-standards, odoo-code-search; при кода: odoo-model-guide, odoo-view-guide,
   odoo-controller-guide (не - няма route), odoo19-frontend (tour-ове),
   odoo19-gotchas, odoo-security-checker, odoo-manifest-validator,
   odoo-multicompany-checker.
2. Имплементация по реда: helpers (allowlist, codecs, transport, fake) с
   unit тестове -> модели -> reader/analyser/importer -> съветници -> изгледи ->
   security -> cron -> демо -> docs. TDD: тестът за allowlist и за „нула команди за
   запис" се пишат ПРЕДИ импортера.
3. Инсталация: `odoo-db-ops` клонинг/свежа база; `-i hr_rfid_hardware_import
   --stop-after-init --no-http`; grep за View error context/Access Rights
   Inconsistency/RELAXNG/does not exist/demo data failed.
   3b. Целият полимекс сет на прясна база с демо: `ir_demo_failure` = 0, всеки
   demo `<record>` в `ir_model_data`, никой модел с меню празен, демото без I/O.
4. Роля QA. 5. Narratives (I). 6. Backend E2E + tour-ове + `/run`+`/verify` за
   крона (cron context) и tour-овете; `--db-filter='^<testdb>$'`.
7. docs/llms.txt + llms-full.md. 8. i18n export -> msgmerge -> po-ai-translator ->
   quality check; тестове под bg. 9. MODULE_INDEX.md (ред + версия, група polimex).
10. code-simplifier + code-reviewer + pr-test-analyzer + silent-failure-hunter
    (има try/except в транспорта) + `/qa-verify`; data-hygiene: cmd.log autovacuum
    (има), survey редове = бизнес данни (не се чистят). 10.5 `/security-review`:
    тригер = нов външен HTTP клиент (transport към модулите) + файлово качване ->
    ЗАДЪЛЖИТЕЛЕН.
11. odoo-precommit A1-A17 (A17: новият модул добавя редове в `ir.model.data`
    module `__import__` - сверка с читателите по `=like` префикс в сестрите),
    таблица с receipts, copy check, diff inspection; версия последна; commit само
    след потвърждение; без клиентски данни в diff-а и в съобщението.

## Верификация (end-to-end)

- Unit: `--test-tags=/hr_rfid_hardware_import` -> 0 failed; allowlist отрицателните
  минават без мрежа.
- E2E: narratives 1-10 зелени на клонинг с bg; проверка `SELECT cmd, cmd_data FROM
  hr_rfid_command` след narrative 1 = само F*/B3 (и F2/B1 за hw 22).
- Tour-ове: 3/3 под bg UI. `/run` + `/verify`: ръчно пускане на крона на клонинг
  с FakeTransport през seam-а и наблюдение на прогреса в UI.
- Живо (само след одобрение на собственика и на тестов обект): опис срещу реален
  webstack със snapshot на `hr.rfid.hw.import.cmd.log` - нито един опкод извън
  allowlist-а; сравнение card_count_device с броя декодирани записи.
- Set gate 3b: прясна база, всички полимекс модули + новия, с демо: 0 demo
  failures, 0 WARNING по grep-а, демо записите налични, menu-моделите непразни.

## Прогрес по изпълнението (2026-09-04)

| Стъпка | Състояние | Доказателство |
|---|---|---|
| 0 папка + план + symlink | готово | тази папка; `odoo19/addons/hr_rfid_hardware_import` |
| 1 скилове | готово | brainstorming, odoo-dev-workflow, wizard-guide, ux-standards, model-guide, view-guide, security-checker, manifest-validator, multicompany-checker, odoo19-gotchas, odoo19-frontend, odoo-translate |
| 2 имплементация | готово | helpers (allowlist, codecs, transport, fake), 13 модела, 4 съветника, изгледи, права, крон, демо, тестове, tour-ове, docs |
| 3 инсталация | готово | прясна база (bg_BG, демо): exit 0, 0 WARNING по grep-а; `-u` след всяка серия промени: exit 0, 0 WARNING |
| 3b целият сет | готово | прясна база (bg_BG, BG, демо), 26 модула от сета: `ir_demo_failure` = 0, 0 модула с demo IS NOT TRUE, 54/54 демо записа, менютата непразни; `-u` на модула: exit 0, 0 WARNING |
| 4-6 QA, разкази, тестове | готово | 10 разказа (раздел I) + формите на отказ -> 96 backend теста + 10 tour-а (един на разказ, всичките под bg UI), 5 оракул теста срещу polimex-protocol 0.1.1 (векторите не са в repo-то, път от `POLIMEX_PROTOCOL_VECTORS`); общо 106 в пакета на модула, 0 паднали |
| живо срещу демо желязото | готово | двата демо модула на лабораторния стенд (адресите ги знае протоколната сесия; само по адрес, без broadcast): 8 контролера, 5 карти, 51 s, само allowlist опкоди, 0 skew; внос в тестовата база: 2 модула (неактивни), 7 контролера с врати/четци, 5 карти с огледални права, 2 групи, 0 команди за запис; пожарният панел отговори с повреден отговор (e=22) - докладвано като шина/окабеляване, добавен повторен опит |
| 7 llms | готово | docs/llms.txt, docs/llms-full.md (без wire детайли) |
| 8 превод | готово | POT 855 низа, bg.po 860/860 през po-ai-translator (sonnet), po_quality_check PASS, без дълги тирета, цитираните имена на бутони сверени знак по знак с преводите на самите бутони |
| 9 индекс | готово | MODULE_INDEX.md ред за модула |
| 10 ревюта | готово | /security-review (без находки >= 8; allow_redirects=False, помощен текст на паролата), code-reviewer (7 приложени, ir.rule остават noupdate по конвенцията на ядрото), pr-test-analyzer (23 нови теста), silent-failure-hunter (C1, C2, H1-H8, M1-M12 приложени), code-simplifier (14 козметични), /qa-verify PASS: 39 адверсарни проби (37 PASS; 2 приети: 65-знаков F0 се търпи, merge_into себе си вече не маркира човека), паритет 10 tour-а / 10 разказа, без icon double-class, без 'undefined' в изгледите, act_window help преведен, 0 кирилски placeholder-а |
| 11 pre-commit одит | готово | odoo-precommit: A1-A16 PASS; четирите лещи дадоха 42 находки, приложени (виж по-долу); 3 отхвърлени с доказателство от ядрото; `ir.rule` под noupdate="1" остава - така са и в hr, stock, account, project, mail |

Решения по пътя:
- Протоколна библиотека (`polimex_protocol`, частно repo): по препоръка на протоколната сесия
  и IP бариерата (публично repo срещу частен протокол) модулът НЕ зависи от нея в runtime;
  тя е тестов еталон. Собственикът поиска начална версия - сложена: polimex-protocol 0.1.0,
  после 0.1.1 (tag polimex-protocol-v0.1.1, 74f16ca) след находка на оракула: маската на
  входовете (FB) се сглобява от 7-битови групи (<<7), както hr_rfid я пише; векторът на
  библиотеката беше грешен (8 бита) и е поправен. Оракулът минава строго (5/5) срещу 0.1.1.
  Странична находка на протоколната сесия (докладвана от нея на собственика, извън моя домейн):
  четенето на FB в ядрото `hr_rfid_webstack.py:1321` има precedence бъг и губи входовете над 7 -
  стойността, която описът чете (вярна), ще се разминава с това, което hr_rfid показва след
  свое четене, докато ядрото не бъде поправено.
- Серийният номер на модула в hr_rfid е до 6 знака; по-дълъг сериен номер спира вноса на
  модула с предупреждение (модулът се удостоверява по серийния си номер).

## Находки от ревютата, приложени на 04.09.2026 (стъпка 10)

Продуктови дефекти, хванати от агентите преди commit (всяко с тест от бизнес страната):
- право по график, който фирмата няма, ставаше право БЕЗ график (врата денонощно) -> остава
  извън вноса с отчетен ред;
- отговор на команда без код на грешка ({}, {"error": ...}) минаваше за успех с празни данни ->
  Unreachable; празен успешен отговор е находка, не настройка;
- код 4 („отказана заявка") се броеше за „не поддържа" при всички контролери и спираше четенето
  на графиците -> предупреждение, останалите слотове се четат;
- смяната на вида служебен собственик от диалога за внос не стигаше до вече създадените
  служебни хора -> write на описа я разнася до непроменените на ръка;
- повторен опис без файл създаваше нови контакти за вече внесени карти -> служебният човек приема
  собственика на съществуващата карта;
- сливане на групи, което ядрото отказва (една врата през две групи, една врата с различни
  условия в една група, набор карти на друга група) -> отказ в съветника с причина; съветникът
  вече е достъпен от формата (бутон „Merge groups...", преди това нямаше път до него от екрана);
- непознат хардуерен тип можеше да стане контролер за достъп с врати -> без врати;
- дълъг сериен номер спираше модула по средата на вноса -> решава се при анализа;
- модул/контролер на друга фирма се назоваваше по име в находката -> „регистриран другаде",
  без име и без връзка; само пропускане;
- has_blockers не зависеше от отметките за графици/хора -> stale гейт при смяна в диалога;
- паролите на паркиран опис (draft/naming/grouping) оставаха безсрочно -> чистят се след 24 ч
  без активност (IDLE_PASSWORD_HOURS), с бележка в чата;
- лог на команда, който не може да се запише, се гълташе -> прекъсва четенето (логът е
  доказателството); мрежово търсене, което не може да тръгне, излизаше като „няма модули" ->
  предупреждение; отговор, който не е JSON обект, или 401/403 -> ясно съобщение; таван на броя
  карти по капацитета на контролера; непълна картова таблица = неуспешно четене, не половин внос;
  паднал модул/контролер може да се прочете отново от стъпка „Имена" (бутон + пренареждане).
- копи: опкодите излязоха от находките (етикет на настройката вместо тях), кодът 22 също.

## Находки от pre-commit одита, приложени на 05.09.2026 (стъпка 11)

Скритите дефекти (никой от тях не се виждаше в зелен пакет, защото файлът с
тестовете за отказите не беше включен в `tests/__init__.py` - самата находка):
- анализът триеше ВСИЧКИ находки от четенето, преди операторът да ги види ->
  находките носят фаза (discovery/read/analysis/import); анализът пренарежда само
  своите и запазва решенията на оператора (резолюции, избран контролер за слот,
  имена на групи с непроменен набор карти);
- непознат хардуерен код или режим 0 влизаха в полета на ядрото с валидация и
  спираха целия внос -> проверка ПРЕДИ create, контролерът се докладва и се пропуска;
- втори паралелен опис никога не се обработваше (кронът се пренасрочваше за
  следващия ден) -> чакащите описи се броят като оставаща работа;
- спрян крон оставяше описа да виси без съобщение -> отказ с указание къде се включва;
- паднал модул се пробваше на всеки пас -> веднъж, после само през „Прочети отново";
- часовник, който не е дата, излизаше като нулево разминаване -> находка;
- членство в група за служител извън отдела по подразбиране (осиновен или от
  предишен опис) гърмеше след половин внос -> всеки засегнат отдел се отваря;
- опис в „спрян" беше мъртъв -> „Отвори отново" връща към стъпката, на която е спрял;
- същият модул по два адреса събаряше откриването -> вторият адрес се оставя настрана;
- ледгерът стана през `ir.model.data._xmlid_to_res_model_res_id` и `_update_xmlids`
  (партидно, поправя ID към изтрит запис); N+1 търсенията и единичните create в
  цикли са партидирани; отдел извън фирмата не може да се избере; смяна на фирмата
  след като има модули е забранена; „Насочи модулите" пропуска вече регистрираните;
- копи: всяко поле, което излиза в изглед, има етикет за потребител (без имена на
  полета и опкоди), текстовете на изключенията не стигат до оператора, „Look again"
  стана „Refresh", цитираните имена на бутони съвпадат с преводите им.

Как се пуска живият опис отново (read-only, само по адрес, без broadcast; производственият
вендинг модул на офиса НИКОГА - адресите са в проектната памет `demo-hardware-live-test`): скрипт през `~/.claude/tools/odoo_shell.py run -d <тестова база>
--script X --commit --addons-path=<абсолютни пътища>`, който създава run с
`discovery_broadcast=False`, добавя двата демо модула по адрес през
`hr.rfid.hw.import.add.ip.wiz`, вика `action_read()` и върти `_cron_process()` +
`env.cr.commit()` до излизане от WORKER_STATES.

Решение на собственика (04.09.2026, след рестарта): протоколната библиотека ще замени цялата
ръчна комуникация в hr_rfid, но не сега - тежко е към момента. За този модул: декодерите и
транспортът остават изолирани в `helpers/` (чисти функции върху hex низове), за да се подменят
с извиквания към библиотеката на едно място, когато hr_rfid мине на нея.
