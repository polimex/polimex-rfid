import xmlrpc.client
import logging

_logger = logging.getLogger(__name__)


class BaseImporter:
    def __init__(self, old_url, old_db, old_username, old_password, new_url, new_db, new_username, new_password,
                 source_version, batch_size=100):
        # Свързване с източниковата система (Odoo 15)
        self.old_url = old_url
        self.old_db = old_db
        self.old_username = old_username
        self.old_password = old_password

        # Свързване с целевата система (Odoo 18)
        self.new_url = new_url
        self.new_db = new_db
        self.new_username = new_username
        self.new_password = new_password

        self.source_version = source_version
        self.batch_size = batch_size

        self.models_old = None
        self.uid_old = None
        self.models_new = None
        self.uid_new = None

        # Свързване с двете системи
        self.connect_to_old_odoo()
        self.connect_to_new_odoo()

    def connect_to_old_odoo(self):
        try:
            common = xmlrpc.client.ServerProxy(f'{self.old_url}/xmlrpc/2/common')
            self.uid_old = common.authenticate(self.old_db, self.old_username, self.old_password, {})
            self.models_old = xmlrpc.client.ServerProxy(f'{self.old_url}/xmlrpc/2/object')
            _logger.info(f'Successfully connected to Odoo {self.source_version} (source): {self.old_url}')
        except Exception as e:
            _logger.error(f'Failed to connect to Odoo {self.source_version} (source): {e}')
            raise

    def connect_to_new_odoo(self):
        try:
            common = xmlrpc.client.ServerProxy(f'{self.new_url}/xmlrpc/2/common')
            self.uid_new = common.authenticate(self.new_db, self.new_username, self.new_password, {})
            self.models_new = xmlrpc.client.ServerProxy(f'{self.new_url}/xmlrpc/2/object')
            _logger.info(f'Successfully connected to Odoo 18 (destination): {self.new_url}')
        except Exception as e:
            _logger.error(f'Failed to connect to Odoo 18 (destination): {e}')
            raise

    def fetch_data_in_batches(self, model, fields, domain=[]):
        offset = 0
        total_records = self.models_old.execute_kw(self.old_db, self.uid_old, self.old_password, model, 'search_count',
                                                   [domain])
        _logger.info(f'Total records in {model}: {total_records}')

        while offset < total_records:
            _logger.info(f'Fetching batch {offset} to {offset + self.batch_size} from {model}')
            records = self.models_old.execute_kw(self.old_db, self.uid_old, self.old_password, model, 'search_read',
                                                 [domain],
                                                 {'fields': fields, 'limit': self.batch_size, 'offset': offset})
            offset += self.batch_size
            yield records

    def check_external_id_exists(self, model, external_id):
        return self.models_new.execute_kw(self.new_db, self.uid_new, self.new_password, 'ir.model.data', 'search_count',
                                          [[('model', '=', model), ('name', '=', external_id)]]) > 0

    def create_external_id(self, model, res_id, external_id):
        self.models_new.execute_kw(self.new_db, self.uid_new, self.new_password, 'ir.model.data', 'create', [{
            'name': external_id,
            'model': model,
            'res_id': res_id,
            'module': 'migration_module'
        }])

    def get_matching_fields(self, source_model, target_model):
        # Извличане на полетата от целевия модел
        target_fields = self.models_new.execute_kw(self.new_db, self.uid_new, self.new_password, target_model,
                                                   'fields_get', [], {'attributes': ['string', 'type']}).keys()

        # Извличане на полетата от източниковия модел
        source_fields = self.models_old.execute_kw(self.old_db, self.uid_old, self.old_password, source_model,
                                                   'fields_get', [], {'attributes': ['string', 'type']}).keys()

        # Сечение на полетата, които съществуват и в двете системи
        matching_fields = [field for field in source_fields if field in target_fields]

        return matching_fields

    def get_avatar_mixin_fields(self):
        # Извличане на всички полета, дефинирани в avatar.mixin от източниковата система
        avatar_mixin_fields = self.models_old.execute_kw(
            self.old_db, self.uid_old, self.old_password,
            'avatar.mixin', 'fields_get', [], {'attributes': ['string', 'type']}
        ).keys()

        return list(avatar_mixin_fields)
    def get_mail_thread_fields(self):
        # Извличане на всички полета, дефинирани в mail.thread от източниковата система
        mail_thread_fields = self.models_old.execute_kw(
            self.old_db, self.uid_old, self.old_password,
            'mail.thread', 'fields_get', [], {'attributes': ['string', 'type']}
        ).keys()

        # Извличане на всички полета, дефинирани в mail.thread.blacklist
        mail_thread_blacklist_fields = self.models_old.execute_kw(
            self.old_db, self.uid_old, self.old_password,
            'mail.thread.blacklist', 'fields_get', [], {'attributes': ['string', 'type']}
        ).keys()

        # Извличане на всички полета, дефинирани в mail.activity.mixin
        mail_activity_mixin_fields = self.models_old.execute_kw(
            self.old_db, self.uid_old, self.old_password,
            'mail.activity.mixin', 'fields_get', [], {'attributes': ['string', 'type']}
        ).keys()

        # Комбиниране на полетата от трите модела
        return list(mail_thread_fields) + list(mail_thread_blacklist_fields) + list(mail_activity_mixin_fields) + self.get_avatar_mixin_fields()

    def get_computed_fields(self, model):
        # Извличане на всички полета с атрибута 'compute' от даден модел
        fields = self.models_old.execute_kw(
            self.old_db, self.uid_old, self.old_password,
            model, 'fields_get', [], {'attributes': ['compute']}
        )

        computed_fields = [field for field, attrs in fields.items() if attrs.get('compute')]
        return computed_fields

    def get_related_fields(self, model):
        # Извличане на всички полета с атрибута 'related' от даден модел
        fields = self.models_old.execute_kw(
            self.old_db, self.uid_old, self.old_password,
            model, 'fields_get', [], {'attributes': ['related']}
        )

        related_fields = [field for field, attrs in fields.items() if attrs.get('related')]
        return related_fields

    def get_model_specific_exceptions(self, model_name):
        # Извличане на полетата от mail.thread, mail.thread.blacklist и mail.activity.mixin
        mail_thread_fields = self.get_mail_thread_fields()

        # Извличане на изчисляващите се полета от източника
        computed_fields = self.get_computed_fields(model_name)

        # Извличане на свързаните полета от източника
        related_fields = self.get_related_fields(model_name)

        # Ръчни изключения, които са общи за всички модели
        common_exclusions = ['self', 'id', 'create_uid', 'create_date', 'write_uid', 'write_date']

        # Ръчни изключения за специфични модели
        manual_exceptions = {
            'res.partner': ['field_to_exclude'],
            'res.users': ['password'],  # Пример за ръчно изключение
            # Добавете ръчни изключения за други модели
        }

        # Комбиниране на ръчните изключения с останалите
        exceptions = mail_thread_fields + computed_fields + related_fields + common_exclusions + manual_exceptions.get(model_name, [])

        return exceptions

    def get_field_mapping(self, model_name):
        # Дефиниране на мапинг за всеки модел
        field_mappings = {
            'res.partner': {
                'old_name': 'name',
                'old_email': 'email',
                # Добавете други мапинги на полета
            },
            'res.users': {
                'old_login': 'login',
                'old_password': 'password',
            },
        }
        return field_mappings.get(model_name, {})

    def get_final_field_mapping(self, source_model, target_model, model_name):
        matching_fields = self.get_matching_fields(source_model, target_model)
        exceptions = self.get_model_specific_exceptions(model_name)
        field_mapping = self.get_field_mapping(model_name)

        # Премахване на изключените полета
        final_fields = [field for field in matching_fields if field not in exceptions]

        # Приложение на мапинга на полетата
        final_mapped_fields = {field: field_mapping.get(field, field) for field in final_fields}

        # Показване на финалните полета, които ще се импортват
        _logger.info(f'Final fields to be imported for {model_name}: {list(final_mapped_fields.values())}')

        return final_mapped_fields

    def map_fields(self, record, field_mapping, source_model):
        mapped_record = {}
        for old_field, new_field in field_mapping.items():
            # Проверка дали полето е many2one или many2many/one2many (по суфикс) и дали стойността не е False
            if old_field.endswith('_id') and record.get(old_field):
                # Извличаме информация за полето, за да получим свързания модел
                field_info = self.models_old.execute_kw(self.old_db, self.uid_old, self.old_password, source_model,
                                                        'fields_get', [old_field])
                related_model = field_info[old_field].get('relation')

                # Ако имаме свързан модел, извършваме импорт на свързания запис
                if related_model:
                    mapped_record[new_field] = self.import_related_model(related_model, record.get(old_field), {})
            elif old_field.endswith('_ids') and record.get(old_field):
                if isinstance(record.get(old_field), list):
                    mapped_record[new_field] = [(6, 0, record.get(old_field))]  # Стандартен many2many формат за Odoo
            else:
                # Прехвърляме директно стойността на полето, ако не е False
                if record.get(old_field) is not False:
                    mapped_record[new_field] = record.get(old_field)

        return mapped_record

    def import_related_model(self, related_model, related_id, related_field_mapping):
        # Импортиране на данни от свързан модел
        if not self.check_external_id_exists(related_model, f'{related_model}_{related_id}'):
            related_data = self.models_old.execute_kw(self.old_db, self.uid_old, self.old_password, related_model,
                                                      'search_read', [[('id', '=', related_id)]],
                                                      {'fields': list(related_field_mapping.keys())})
            if related_data:
                mapped_related_data = self.map_fields(related_data[0], related_field_mapping)
                new_related_record = self.models_new.execute_kw(self.new_db, self.uid_new, self.new_password,
                                                                related_model, 'create', [mapped_related_data])
                self.create_external_id(related_model, new_related_record, f'{related_model}_{related_id}')
                return new_related_record
        else:
            _logger.info(f'Skipping import of related {related_model} with ID {related_id}, already exists.')
            return self.models_new.execute_kw(self.new_db, self.uid_new, self.new_password, related_model, 'search',
                                              [[('id', '=', related_id)]])[0]

    def import_log_notes(self, source_model, target_model, record_id, new_record_id):
        # Извличане на съобщенията от източниковата система за конкретния запис
        log_messages = self.models_old.execute_kw(self.old_db, self.uid_old, self.old_password, 'mail.message',
                                                  'search_read', [
                                                      [('res_id', '=', record_id), ('model', '=', source_model),
                                                       ('message_type', '=', 'comment'), ('author_id', '!=', False)]],
                                                  {'fields': ['body', 'author_id', 'date']})

        for message in log_messages:
            # Прехвърляне на съобщенията към целевата система
            self.models_new.execute_kw(self.new_db, self.uid_new, self.new_password, 'mail.message', 'create', [{
                'body': message['body'],
                'author_id': message['author_id'][0],
                'date': message['date'],
                'model': target_model,
                'res_id': new_record_id,
                'message_type': 'comment',
            }])
            _logger.info(f'Log note for record {new_record_id} in {target_model} has been migrated.')

    def import_data(self, model, data, external_id, source_model, record_id):
        # Проверка дали записът вече съществува
        if not self.check_external_id_exists(model, external_id):
            # Създаване на нов запис
            new_record_id = self.models_new.execute_kw(self.new_db, self.uid_new, self.new_password, model, 'create',
                                                       [data])
            self.create_external_id(model, new_record_id, external_id)
            _logger.info(f'Successfully imported {model}: {external_id}')

            # Прехвърляне на лог съобщенията
            self.import_log_notes(source_model, model, record_id, new_record_id)
        else:
            # Ако записът съществува, намираме неговия ID и правим ъпдейт
            record_id = self.models_new.execute_kw(self.new_db, self.uid_new, self.new_password, model, 'search',
                                                   [[('id', '=', external_id)]])[0]
            self.models_new.execute_kw(self.new_db, self.uid_new, self.new_password, model, 'write',
                                       [[record_id], data])
            _logger.info(f'Updated existing record in {model}: {external_id}')

            # Прехвърляне на лог съобщенията
            self.import_log_notes(source_model, model, record_id, record_id)

    def import_data_for_model(self, source_model, target_model=None, ignored_ids=None):
        # Ако няма зададен целеви модел, използваме същия като източниковия
        if target_model is None:
            target_model = source_model

        # Ако няма зададен списък с IDs, които да се игнорират, създаваме празен списък
        if ignored_ids is None:
            ignored_ids = []

        # Извличане на полетата за мапинг
        field_mapping = self.get_final_field_mapping(source_model, target_model, source_model)

        # Извличане на данни на партиди и пропускане на записи с IDs от списъка ignored_ids
        for batch in self.fetch_data_in_batches(source_model, list(field_mapping.keys())):
            for record in batch:
                if record['id'] in ignored_ids:
                    _logger.info(
                        f'Skipping record {record["id"]} from {source_model} due to being in ignored_ids list.')
                    continue  # Пропускаме записа, ако ID-то е в списъка с игнорирани

                # Тук добавяме source_model към извикването на map_fields
                mapped_data = self.map_fields(record, field_mapping, source_model)
                external_id = f'{source_model}_{record["id"]}'
                self.import_data(target_model, mapped_data, external_id, source_model, record['id'])


class PartnerImporter(BaseImporter):
    def import_partners(self, target_model=None, ignored_ids=None):
        source_model = 'res.partner'
        if target_model is None:
            target_model = source_model
        # Стартиране на миграцията на партньори
        self.import_data_for_model(source_model, target_model=target_model, ignored_ids=ignored_ids)



def test_import_partners():
    # Настройки за връзка с Odoo 15 (Източник)
    old_url = 'http://localhost:8015'
    old_db = '15_rfid_customer_plastimo'
    old_username = 'polimex'
    old_password = 'polimex1206'

    # Настройки за връзка с Odoo 18 (Цел)
    new_url = 'http://localhost:8018'
    new_db = '18_dev'
    new_username = 'admin'
    new_password = 'admin'

    source_version = 15  # Версия на източника

    # Извикване на миграцията за партньори с целеви модел и списък с игнорирани IDs
    ignored_ids = [1, 2, 3]  # Примерен списък с IDs за игнориране
    partner_importer = PartnerImporter(old_url, old_db, old_username, old_password, new_url, new_db, new_username,
                                       new_password, source_version)
    partner_importer.import_partners(target_model='res.partner', ignored_ids=ignored_ids)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    _logger = logging.getLogger(__name__)

    try:
        _logger.info('Starting partner migration...')
        test_import_partners()
        _logger.info('Partner migration completed successfully.')
    except Exception as e:
        _logger.error(f'Error during migration: {e}')
