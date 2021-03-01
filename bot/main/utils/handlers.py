import logging

class ConsoleHandler(logging.StreamHandler):
    def emit(self, record):
        record.msg = record.msg.encode('utf-8', errors='replace')
        logging.StreamHandler.emit(self, record)
