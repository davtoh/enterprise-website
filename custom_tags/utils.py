from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string
import random
import logging
from django.db import connection, migrations
from django.db.utils import Error
import os
import io
import json
import sqlparse
#from django.db import connections
#connections.close_all()

logger = logging.getLogger('django')


class LoggerCommand(BaseCommand):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logger

    def handle(self, *args, **options):
        verbosity = options.get('verbosity')
        if verbosity == 0:
            self.logger.setLevel(logging.WARN)
        elif verbosity == 1:  # default
            self.logger.setLevel(logging.INFO)
        elif verbosity == 2:
            self.logger.setLevel(logging.DEBUG)


def load_source(fn, cache=True, replacements=None, verbose=True):

    # select json cached file
    if fn.endswith(".json"):
        cached_fn = fn
    else:
        cached_fn = fn+".json"

    # check there is a json cache
    if cache and os.path.exists(cached_fn):
        logger.info("Loading cache file")
        # load json cache
        with io.open(cached_fn, encoding="utf8") as f:
            lines = json.loads(f.read())
    else:
        # create json cache
        logger.info("Loading source file")
        # load source
        with io.open(fn, encoding="utf8") as f:
            source = f.read()

        # modify source according to models
        # the original database comes with `countries` `regions` `cities` tables so we have to replace those
        modified_source = source
        if replacements:
            logger.info("Modifying source")
            for i, j in replacements.items():
                modified_source = modified_source.replace(i, j)

        logger.info("Parsing source file")
        raw_lines = sqlparse.split(modified_source)
        lines = [i for i in raw_lines if i]  # anly lines with commands

        # save json model
        if cache:
            logger.info("Saving cache file to '{}'".format(cached_fn))
            try:
                with open(cached_fn, 'wb+') as f:
                    f.write(json.dumps(lines).encode("utf8"))
            except IOError:
                pass  # allow the program to continue even if cache file is not completed

    with connection.cursor() as cursor:
        size = len(lines)
        show_until = 20
        for i, l in enumerate(lines):
            try:
                logger.info("Executing command {} of {}>{}...".format(i+1, size, l[:show_until]))
                cursor.execute(l)
            except Error:
                logger.error("Error in command {} of {}>{}...".format(i+1, size, l[:show_until]))
                raise


def generate_key(length=50, chars=None, django_method=True):
    """
    Generate a random key.

    :param length: number of characters on generated key
    :param chars: a string of characters to use
    :param django_method: True to use default django encryption or False to use System random
    :return: string of generated key
    """
    if not chars:
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'

    if django_method:
        # https://stackoverflow.com/a/16630719
        return get_random_string(length, chars)
    else:
        return ''.join([random.SystemRandom().choice(chars) for _ in range(length)])
