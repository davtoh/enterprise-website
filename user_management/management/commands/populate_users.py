from user_management.models import SiteUser
from custom_tags.utils import LoggerCommand
from django.db.utils import IntegrityError


class Command(LoggerCommand):
    #args = '<foo bar ...>'
    help = 'Create generic users for testing. "superuser", "staff" and "regular" types' \
           '\n can be created with the password as the username if not password is specified.' \
           '\n e.g. --staff username1, password1, ..., usernameN, passwordN' \
           '\n      --staff username1' \
           '\n (WARNING: creating test users can be dangerous as the passwords are known)'
    requires_migrations_checks = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update = False

    def add_arguments(self, parser):

        # Named (optional) arguments
        parser.add_argument(
            '-s',
            '--superuser',
            action='store',
            nargs='*',
            default=[],
            help='Create superuser user which has all permissions. -s <name>',
        )
        parser.add_argument(
            '-f',
            '--staff',
            action='store',
            nargs='*',
            default=[],
            help='Create staff user which has limited permissions',
        )
        parser.add_argument(
            '-r',
            '--regular',
            action='store',
            nargs='*',
            default=[],
            help='Create regular user which does not have permissions',
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Create "superuser", "staff" and "regular" user types with username and password as their types',
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update password if user already exits',
        )

    def _create_supersuer(self, username='superuser', password=None):
        if password is None:
            password = username
        try:
            user = SiteUser.objects.create_user(username=username, password=password, is_active=True, is_superuser=True, is_staff=True)
            user.save()
            self.logger.info("created superuser '{}'".format(username))
        except IntegrityError:
            # user already exits update password
            if self.update:
                user = SiteUser.objects.get(username__exact=username)
                if password and user.is_superuser:
                    user.set_password(password)
                    user.save()
                    self.logger.info("Password for superuser '{}' updated".format(username))
            else:
                self.logger.info("User '{}' already exists".format(username))

    def _create_staff(self, username='staff', password=None):
        if password is None:
            password = username
        try:
            user = SiteUser.objects.create_user(username=username, password=password, is_active=True, is_superuser=False, is_staff=True)
            user.save()
            self.logger.info("created staff user '{}'".format(username))
        except IntegrityError:
            # user already exits update password
            if self.update:
                user = SiteUser.objects.get(username__exact=username)
                if password and user.is_staff:
                    user.set_password(password)
                    user.save()
                    self.logger.info("Password for staff user '{}' updated".format(username))
            else:
                self.logger.info("User '{}' already exists".format(username))

    def _create_regular(self, username='regular', password=None):
        if password is None:
            password = username
        try:
            user = SiteUser.objects.create_user(username=username, password=password, is_active=True, is_superuser=False, is_staff=False)
            user.save()
            self.logger.info("created regular user '{}'".format(username))
        except IntegrityError:
            # user already exits update password
            if self.update:
                user = SiteUser.objects.get(username__exact=username)
                if password and not user.is_staff and not user.is_superuser:
                    user.set_password(password)
                    user.save()
                    self.logger.info("Password for regular user '{}' updated".format(username))
            else:
                self.logger.info("User '{}' already exists".format(username))

    def _handle_args(self, lists, method):
        for i in range(0, len(lists), 2):
            # format: [username1, password1, ..., usernameN, passwordN]
            method(*lists[i:i+1])

    def handle(self, *args, **options):

        self.update = int(options['update'])

        if options['test']:
            # create default test users
            self._create_supersuer()
            self._create_staff()
            self._create_regular()
        else:
            # create custom test users
            self._handle_args(options['superuser'], self._create_supersuer)
            self._handle_args(options['staff'], self._create_staff)
            self._handle_args(options['regular'], self._create_regular)
