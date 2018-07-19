from custom_tags.utils import LoggerCommand, generate_key
from django.conf import settings as _settings
from django.core.exceptions import ImproperlyConfigured
import json
import os
import platform

# settings
PLATFORM = platform.system().upper()
DEFAULT_KEYS = {
  "SECRET_KEY": "",
  "DB_USER": "root",
  "DB_PASS": "",
  "YANDEX_TRANSLATE_KEY": ""
}


def load_secret_file():
    """
    extract SECRET_FILE from settings
    """
    try:
        return _settings.SECRET_FILE
    except (ImproperlyConfigured, AttributeError):
        # called from an un-configured settings.py then create dummy value
        return "keys.json"


class Command(LoggerCommand):
    help = 'Create or manage generic {} file for settings.py sensitive data configuration' \
           '\n'.format(load_secret_file())
    requires_migrations_checks = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser = None

    def add_arguments(self, parser):
        self.parser = parser

        # Named (optional) arguments
        parser.add_argument(
            '-f',
            '--fill',
            action='store_true',
            help='Fill all the fields asking the user to provide the data',
        )
        parser.add_argument(
            '-k',
            '--key',
            nargs=2,
            action='append',
            default=[],
            help='Add a key with its value. e.g. -k MY_KEY_1 MY_VALUE_1 ... -k MY_KEY_N MY_VALUE_N',
        )
        parser.add_argument(
            '-r',
            '--revert',
            nargs=1,
            action='append',
            default=[],
            help='revert updated key which is cached with a prefix "OLD_". e.g. -r MY_KEY_1 ... -r MY_KEY_N',
        )
        parser.add_argument(
            '-g',
            '--generate',
            nargs="*",
            action='append',
            default=[],
            help='generate key with arbitrary length and characters set. '
                 '\ne.g. -g MY_KEY_1 -g MY_KEY_2 LENGTH CHAR_SET ... -g MY_KEY_N',
        )
        parser.add_argument(
            '-p',
            '--path',
            action='store',
            default=load_secret_file(),
            help='Path to file. It is by default \'{}\''.format(load_secret_file()),
        )
        parser.add_argument(
            '-u',
            '--update',
            action='store_true',
            help='Update any key that has been already defined. This can be combines with the --fill option',
        )

    def load_keys_file(self, fn, force=True):
        """
        loads {} file or creates it if does not exists.

        :param fn: file path
        :param force: True to force keys file generation if does not exits
        :return:
        """
        # print("Called from command line: {}".format(self._called_from_command_line))
        try:
            with open(fn, "r") as f:
                self.logger.info("loading secret keys file '{}'".format(fn))
                return json.load(f)
        except FileNotFoundError:
            if not force:
                raise
            self.logger.warning("secret keys file '{}' was not found and will be generated".format(fn))
            return self.generate_keys_file(fn)

    load_keys_file.__doc__ = load_keys_file.__doc__.format(load_secret_file())

    def generate_keys_file(self, fn, **keys):
        """
        Generate keys file.

        :param fn: path to keys file
        :param keys: dictionary updating de default keys
        :return: loaded keys
        """

        # update with user defined keys
        for k, v in DEFAULT_KEYS.items():
            if k not in keys:
                self.logger.info("adding default '{}' key".format(k))
                keys[k] = v

        # ensure secret key exists and is valid
        if not keys.get("SECRET_KEY"):
            keys["SECRET_KEY"] = generate_key(50)

        # save
        self.logger.info("{} secret keys file '{}'".format(["creating", "updating"][os.path.exists(fn)], fn))
        with open(fn, "w") as f:
            json.dump(keys, f)

        return keys

    def handle(self, *args, **options):

        # get keys file path
        fn = options['path']

        # load keys
        try:
            keys = self.load_keys_file(fn, force=False)
        except FileNotFoundError:
            keys = {}

        # revert keys
        for k in options['revert']:
            r = "OLD_" + k
            if r in keys:
                self.logger.info("reverting '{}' key".format(k))
                keys[k] = keys[r]  # make backup
            else:
                self.logger.warning("cannot revert '{}' key".format(k))

        # create provided keys
        provided_keys = dict(options['key'])

        # insert generated keys
        def convert_bool(x):
            if x == "true":
                return True
            elif x == "false":
                return False
            else:
                self.parser.error("'{}' is not recognized as a boolean operation".format(x))

        # create conversions to parse command
        conversions = [len, None, convert_bool]
        for command in options['generate']:

            # parse command
            k, parse = command[0], command[1:]

            if len(parse) > len(conversions):
                self.parser.error("command '{}' has more than 4 arguments".format(" ".join(command)))

            if k in provided_keys:
                self.logger.warning("'{}' key with -g replaced by -k option".format(k))
                continue

            if k in keys and not options["update"]:
                self.logger.warning("ignoring generation of '{}' key. Use --update to update.".format(k))
                continue

            for i, sub in enumerate(parse):
                f = conversions[i]
                if f is not None:
                    parse[i] = f(sub)

            self.logger.info("generating '{}' key".format(k))
            provided_keys[k] = generate_key(*parse)

        # insert from provided keys
        for k, v in provided_keys.items():

            if keys.get(k):
                if options['update']:
                    # key k exits and is intended to be updated
                    self.logger.info("updating '{}' key".format(k))
                    keys["OLD_" + k] = keys[k]  # make backup
                    keys[k] = v
                else:
                    # key k exits and must not be updated
                    self.logger.warning("ignoring existent '{}' key. Use --update to update.".format(k))
            else:
                # key k does not exits or is empty
                self.logger.info("adding '{}' key".format(k))
                keys[k] = v

        # let the user manually change the keys
        if options['fill']:

            def fillout(k, v):
                if v:
                    if options['update']:
                        ans = input("'{}':'{}' do you wish to change it? (y,n): ".format(k, v)).lower()
                        if ans.startswith("y"):
                            keys[k] = input("Insert value for '{}': ".format(k))
                else:
                    keys[k] = input("Insert value for '{}': ".format(k))

            for k, v in keys.items():
                fillout(k, v)

            # lets the user fill DEFAULT_KEYS
            options['update'] = True  # force update to change default values. if not they will be added on save
            for k, v in [(k, v) for k, v in DEFAULT_KEYS.items() if k not in keys]:
                fillout(k, v)

        # save
        self.generate_keys_file(fn, **keys)
