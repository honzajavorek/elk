# -*- coding: utf-8 -*-


import os
import sys

from gi.repository import Notify
from send2trash import send2trash


system_encoding = sys.getfilesystemencoding()


def list_files(directory, exts=None, recursive=False):
    if exts is not None:
        exts = frozenset('.' + ext.lstrip('.') for ext in exts)

    def list_dir(directory):
        for basename in os.listdir(directory):
            filename = os.path.join(directory, basename)
            if recursive and os.path.isdir(filename):
                for filename in list_files(filename, exts, recursive=True):
                    yield filename
                continue
            elif exts and not os.path.splitext(filename)[1].lower() in exts:
                continue
            yield filename

    return sorted(list_dir(directory))


def season(d):
    if 3 <= d.month <= 5:
        return u'jaro'
    if 6 <= d.month <= 8:
        return u'léto'
    if 9 <= d.month <= 11:
        return u'podzim'
    return 'zima'


def notify(name, message):
    Notify.init(name)
    n = Notify.Notification.new(name, message, 'dialog-information')
    n.show()


def to_trash(filename):
    try:
        send2trash(filename)
    except OSError as e:
        if e.errno == 13:  # permission denied
            os.remove(filename)
        else:
            raise
