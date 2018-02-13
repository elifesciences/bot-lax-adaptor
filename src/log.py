import logging
from pythonjsonlogger import jsonlogger
import dateutils

def setup_root_logger():
    root_logger = logging.getLogger("")

    # output to stderr
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)

    class FormatterWithEncodedExtras(logging.Formatter):
        def format(self, record):
            # exclude all known keys in Record
            # bundle the remainder into an 'extra' field,
            # bypassing attempt to make Record read-only
            _known_keys = [
                'asctime', 'created', 'filename', 'funcName', 'levelname', 'levelno', 'lineno',
                'module', 'msecs', 'message', 'name', 'pathname', 'process', 'processName',
                'relativeCreated', 'thread', 'threadName',
                # non-formatting fields present in __dict__
                'exc_text', 'exc_info', 'msg', 'args',
            ]
            unknown_fields = {key: val for key, val in record.__dict__.items() if key not in _known_keys}
            record.__dict__['extra'] = dateutils.json_dumps(unknown_fields)
            return super(FormatterWithEncodedExtras, self).format(record)

    handler.setFormatter(FormatterWithEncodedExtras('%(levelname)s - %(asctime)s - %(message)s -- %(extra)s'))

    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)

def json_formatter():
    supported_keys = [
        'asctime',
        #'created',
        'filename',
        'funcName',
        'levelname',
        #'levelno',
        'lineno',
        'module',
        #'msecs',
        'message',
        'name',
        'pathname',
        #'process',
        #'processName',
        #'relativeCreated',
        #'thread',
        #'threadName'
    ]

    # optional json logging if you need it
    log_format = ['%({0:s})'.format(i) for i in supported_keys]
    log_format = ' '.join(log_format)
    return jsonlogger.JsonFormatter(log_format)
