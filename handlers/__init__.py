# handlers/__init__.py
from .commands import (
    start_command,
    help_command,
    thumb_command,
    delthumb_command,
    photo_handler,
    cancel_command,
    stats_command,
)
from .text_handler import txt_document_handler, text_response_handler
