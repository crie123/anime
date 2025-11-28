# Localization strings for Anime Collection

TRANSLATIONS = {
    'en': {
        # Window and general
        'app_title': 'Anime Collection',
        'close': 'Close',
        
        # Menu buttons
        'add': 'Add',
        'edit': 'Edit',
        'delete': 'Delete',
        'import': 'Import',
        'export': 'Export',
        'search': 'Search anime...',
        'tags': 'Tags',
        'sort': 'Sort',
        'select_anime': 'Select Anime',
        
        # Sort options
        'a_z': 'A-Z',
        'z_a': 'Z-A',
        'date_added': 'Date Added',
        'all': 'All',
        
        # Details panel
        'select_an_anime': 'Select an anime',
        'delete_anime': 'Delete Anime',
        'title': 'Title:',
        'poster': 'Poster:',
        'screenshots': 'Screenshots:',
        'description': 'Description:',
        'tags_label': 'Tags:',
        'browse': 'Browse',
        
        # Popup titles
        'add_new_anime': 'Add New Anime',
        'edit_anime': 'Edit Anime',
        'confirm_delete': 'Confirm Delete',
        'delete_title': "Delete '{}'?",
        'export_data': 'Export Data',
        'import_data': 'Import Data',
        'filter_by_tags': 'Filter by tags',
        'bulk_delete': 'Bulk Delete',
        'bulk_edit': 'Bulk Edit',
        'yes': 'Yes',
        'no': 'No',
        'ok': 'OK',
        'save': 'Save',
        'cancel': 'Cancel',
        'apply': 'Apply',
        'select': 'Select',
        'export_to_json': 'Export to JSON',
        'import_from_json': 'Import from JSON',
        'filename': 'Filename (for save)',
        'export_successful': 'Export Successful',
        'exported_to': 'Exported to {}',
        'export_failed': 'Export Failed',
        'import_successful': 'Import Successful',
        'import_completed': 'Import Completed with errors',
        'import_failed': 'Import Failed',
        'importing': 'Importing...',
        'added': 'Added',
        'anime_added': "Anime '{}' added",
        'updated': 'Updated',
        'anime_updated': "Anime '{}' updated",
        'no_items_selected': 'No items selected',
        'delete_items': 'Delete {} items?',
        'enter_tags': 'Enter tags (comma separated) to set for selected items',
        'bulk_edit_tags': 'Bulk Edit Tags',
        'imported_skipped': 'Imported: {}. Skipped: {}.',
        'enter_anime_title': 'Enter anime title',
        'enter_poster_path': 'Enter poster path',
        'enter_screenshot_paths': 'Enter screenshot paths (comma separated)',
        'enter_anime_description': 'Enter anime description',
        'enter_tags_input': 'Enter tags (comma separated)',
        'validation_error': 'Validation Error',
        'title_required': 'Title is required',
    },
    'ru': {
        # Window and general
        'app_title': 'Коллекция Аниме',
        'close': 'Закрыть',
        
        # Menu buttons
        'add': 'Добавить',
        'edit': 'Изменить',
        'delete': 'Удалить',
        'import': 'Импорт',
        'export': 'Экспорт',
        'search': 'Поиск аниме...',
        'tags': 'Теги',
        'sort': 'Сортировка',
        'select_anime': 'Выбрать Аниме',
        
        # Sort options
        'a_z': 'А-Я',
        'z_a': 'Я-А',
        'date_added': 'По дате добавления',
        'all': 'Все',
        
        # Details panel
        'select_an_anime': 'Выберите аниме',
        'delete_anime': 'Удалить Аниме',
        'title': 'Название:',
        'poster': 'Постер:',
        'screenshots': 'Скриншоты:',
        'description': 'Описание:',
        'tags_label': 'Теги:',
        'browse': 'Обзор',
        
        # Popup titles
        'add_new_anime': 'Добавить Новое Аниме',
        'edit_anime': 'Редактировать Аниме',
        'confirm_delete': 'Подтвердить удаление',
        'delete_title': "Удалить '{}'?",
        'export_data': 'Экспорт данных',
        'import_data': 'Импорт данных',
        'filter_by_tags': 'Фильтр по тегам',
        'bulk_delete': 'Массовое удаление',
        'bulk_edit': 'Массовое редактирование',
        'yes': 'Да',
        'no': 'Нет',
        'ok': 'ОК',
        'save': 'Сохранить',
        'cancel': 'Отмена',
        'apply': 'Применить',
        'select': 'Выбрать',
        'export_to_json': 'Экспортировать в JSON',
        'import_from_json': 'Импортировать из JSON',
        'filename': 'Имя файла (для сохранения)',
        'export_successful': 'Экспорт успешен',
        'exported_to': 'Экспортировано в {}',
        'export_failed': 'Ошибка экспорта',
        'import_successful': 'Импорт успешен',
        'import_completed': 'Импорт завершен с ошибками',
        'import_failed': 'Ошибка импорта',
        'importing': 'Импортирование...',
        'added': 'Добавлено',
        'anime_added': "Аниме '{}' добавлено",
        'updated': 'Обновлено',
        'anime_updated': "Аниме '{}' обновлено",
        'no_items_selected': 'Элементы не выбраны',
        'delete_items': 'Удалить {} элементов?',
        'enter_tags': 'Введите теги (разделённые запятыми) для выбранных элементов',
        'bulk_edit_tags': 'Массовое редактирование тегов',
        'imported_skipped': 'Импортировано: {}. Пропущено: {}.',
        'enter_anime_title': 'Введите название аниме',
        'enter_poster_path': 'Введите путь к постеру',
        'enter_screenshot_paths': 'Введите пути скриншотов (разделённые запятыми)',
        'enter_anime_description': 'Введите описание аниме',
        'enter_tags_input': 'Введите теги (разделённые запятыми)',
        'validation_error': 'Ошибка валидации',
        'title_required': 'Название обязательно',
        'no_anime_available': 'Нет доступного аниме',
    }
}

class Localization:
    def __init__(self, language='en'):
        self.language = language if language in TRANSLATIONS else 'en'
        self.strings = TRANSLATIONS[self.language]
    
    def set_language(self, language):
        if language in TRANSLATIONS:
            self.language = language
            self.strings = TRANSLATIONS[language]
    
    def get(self, key, *args):
        """Get localized string with optional formatting"""
        text = self.strings.get(key, key)
        if args:
            try:
                return text.format(*args)
            except:
                return text
        return text
    
    def __getitem__(self, key):
        return self.strings.get(key, key)

# Global localization instance
i18n = Localization('en')

def set_language(lang):
    """Set global language"""
    i18n.set_language(lang)

def tr(key, *args):
    """Translate string (shorthand)"""
    return i18n.get(key, *args)
