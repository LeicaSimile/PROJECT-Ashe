import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class Logger(object):
    @classmethod
    def debug(cls, log_object, msg, *args, **kwargs):
        cls._log(log_object, logging.DEBUG, msg, *args, **kwargs)

    @classmethod
    def info(cls, log_object, msg, *args, **kwargs):
        cls._log(log_object, logging.INFO, msg, *args, **kwargs)

    @classmethod
    def warn(cls, log_object, msg, *args, **kwargs):
        cls._log(log_object, logging.WARN, msg, *args, **kwargs)

    @classmethod
    def error(cls, log_object, msg, *args, **kwargs):
        cls._log(log_object, logging.ERROR, msg, *args, **kwargs)

    @classmethod
    def critical(cls, log_object, msg, *args, **kwargs):
        cls._log(log_object, logging.CRITICAL, msg, *args, **kwargs)

    @classmethod
    def _log(cls, log_object, log_level, message, *args, **kwargs):
        log_map = {
            logging.DEBUG: log_object.debug,
            logging.INFO: log_object.info,
            logging.WARN: log_object.warn,
            logging.ERROR: log_object.error,
            logging.CRITICAL: log_object.critical,
        }
        try:
            log_map[log_level](message, *args, **kwargs)
        except UnicodeEncodeError:
            log_map[log_level](message.encode("utf-8", errors="replace"), *args, **kwargs)
        except AttributeError as invalid_arg_err:
            logger.error(invalid_arg_err)
