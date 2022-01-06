import sys
import logging

# метод определения модуля, источника запуска.
if sys.argv[0].find('client') == -1:
    # если сервер
    logger = logging.getLogger('server')
else:
    # если клиент
    logger = logging.getLogger('client')


def log(func_to_log):
    def log_saver(*args, **kwargs):
        logger.debug(
            f'Была вызвана функция {func_to_log.__name__} '
            f'c параметрами {args}, '
            f'{kwargs}. Вызов из модуля {func_to_log.__module__}')
        ret = func_to_log(*args, **kwargs)
        return ret

    return log_saver
