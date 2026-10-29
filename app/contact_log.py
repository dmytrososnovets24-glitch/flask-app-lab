import logging
import os

_handlers = {}


def _get_logger(path):
    """Повертає logger, що дописує у файл `path` (створює каталог, якщо його немає)."""
    logger = logging.getLogger(f'contact_form.{path}')
    if path not in _handlers:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        handler = logging.FileHandler(path, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
        logger.setLevel(logging.INFO)
        logger.propagate = False
        logger.addHandler(handler)
        _handlers[path] = handler
    return logger


def log_contact_message(path, form):
    """Дописує дані контактної форми у лог-файл. Кидає OSError, якщо запис неможливий."""
    message = ' '.join(form.message.data.split())  # один рядок у лозі
    line = (f'name={form.name.data} | email={form.email.data} | phone={form.phone.data} | '
            f'subject={form.subject_label()} | message={message}')
    logger = _get_logger(path)
    logger.info(line)
    for handler in logger.handlers:
        handler.flush()
