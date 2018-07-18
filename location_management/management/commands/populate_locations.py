from location_management.models import Countries, States, Cities
from custom_tags.utils import LoggerCommand, load_source

# https://docs.djangoproject.com/en/2.0/topics/db/sql/
# https://docs.djangoproject.com/en/2.0/ref/migration-operations/
# https://dev.mysql.com/doc/refman/8.0/en/load-data.html
# https://www.geodatasource.com/world-cities-database/free
# https://github.com/prograhammer/countries-regions-cities
# https://stackoverflow.com/a/45759226/5288758

# the original database comes with `countries` `regions` `cities` tables so we have to replace those
replacements = {"`countries`": "`{}`".format(Countries._meta.db_table),
                "`regions`": "`{}`".format(States._meta.db_table),
                "`cities`": "`{}`".format(Cities._meta.db_table),
                "`region_id`": "`state_id`",
                }


class Command(LoggerCommand):
    args = '<path/to_database/>'
    help = 'Load World database to fill Countries, States and Cities. ' \
           '\nThis takes about 1 hour if it is not cached.'

    def handle(self, *args, **options):
        path = "./world.sql" if not args else args[0]
        load_source(fn=path, replacements=replacements, cache=True)
