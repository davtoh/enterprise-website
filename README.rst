WEB PAGE DOCUMENTATION:
=======================

This projects intents to provide a base web page for industrial or commercial businesses that intent to offer their
products, services or just want to advertise their enterprise online.

# INSTALLATION INSTRUCTIONS:

## ON LINUX:
### Install Mysql
instructions from https://www.digitalocean.com/community/tutorials/how-to-install-mysql-on-ubuntu-18-04
$ sudo apt update
$ sudo apt install mysql-server
$ sudo mysql_secure_installation

### Run additional commands to allow phpMyAdmin
$ sudo mysql
mysql> SELECT user,authentication_string,plugin,host FROM mysql.user;
mysql> ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'password';
mysql> FLUSH PRIVILEGES;
mysql> SELECT user,authentication_string,plugin,host FROM mysql.user;
mysql> exit

### Add user for web page's database
$ mysql -u root -p
mysql> CREATE DATABASE productsDB;
mysql> CREATE USER 'user'@'localhost' IDENTIFIED BY 'Somepass123.';
mysql> GRANT ALL PRIVILEGES ON productsDB.* TO 'user'@'localhost' WITH GRANT OPTION;
mysql> exit

## ON ANY MACHINE

After installing the basic programs (i.e. MySQL, python, git) on the server machine follow the remaining instructions to
setup the project

#. cloning the repository
$ git clone https://github.com/davtoh/product-web-page.git

#. Installing requirements
$ pip install requirements.txt

#. create the ``keys.json`` configuration file for sensitive data
To protect sensitive data the keys.json file is loaded on the settings.py file and used to provide the necessary keys.
If ti is not provided a generic file will be created and a generic ``SECRET_KEY`` provided. The default file
``keys.json`` has the form:

```
{
  "SECRET_KEY":"provide_sensitive_key",
    ....
  "OTHER_RELEVANT_KEY":"provide_sensitive_key"
}
```
The default keys are:

* ``"SECRET_KEY"``: it must be a long key of 50 characters.
* ``"DB_USER_{PLATFORM}"``: the user name for the database. Notice that the key is generated for an
    specific OS. Thus it would be ``"DB_USER_WINDOWS"``, ``"DB_USER_LINUX"`` and ``"DB_USER_DARWIN"`` on Windows, Linux and Mac
    OSs respectively.
* ``"DB_PASS_{PLATFORM}"``: the password for the user name on the database. Notice that the key is generated for an
    specific OS. Thus it would be ``"DB_PASS_WINDOWS"``, ``"DB_PASS_LINUX"`` and ``"DB_PASS_DARWIN"`` on Windows, Linux and Mac
    OSs respectively.
* ``"YANDEX_TRANSLATE_KEY"`` is used to generate possible translations on the rosetta plugin helping the translators
    accomplish their tasks faster. You can get a key registering on https://www.yandex.com/ for free (as of now).

.. note::
    A specific key for a platform takes precedence over a general key. Thus ``"DB_USER_{PLATFORM}"`` replaces
    ``"DB_USER"`` if it exits. This is a implementation decision to port the web page but the same time differentiate
    between local configurations in the OS. The ``"SECRET_KEY"`` key and others don't use this behaviour as they
    don't depend on the system configuration and the database data can be shared among OSs.

the keys files can be created or managed using the ``secret_keys`` command. Type the following command to get help

$ python manage.py secret_keys --help

#. Run migrations
Once the database is created it is necessary to create the tables reflecting the models used on the web page. Run
the following commands if the project's ``settings.py`` file is configured with the database.

$ python manage.py makemigrations
$ python manage.py migrate

#. Create admin user
It is a good practice to create a superuser that will have control over all the web page and use it exclusively
to create staff users which will have lower permissions to administer the web page. This superuser is usually the
owner of the enterprise if there is just one or an user that represents all the enterprise and that will be kept
secret to employees, only accessible to higher-ups.

$ python manage.py createsuperuser --username=admin --email=email@messages.com

#. (Optional) Create debug users
$ python manage.py populate_users --test

.. warning::
    --test creates generic users: ``"superuser"``, ``"staff"`` and ``"regular"`` with the passwords the same as their names
    and it should not be used for production. This can cause a breach so only use for debugging or testing and
    delete after uses

#. Additional resources and databases
Download the following resources, extract and place them on the working directory:

* [world.sql](https://github.com/prograhammer/countries-regions-cities)
* [GeoLiteCity.dat](http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz)
* [GeoLiteCityv6.dat](http://geolite.maxmind.com/download/geoip/database/GeoLiteCityv6-beta/GeoLiteCityv6.dat.gz)

This files are used as pre-loaded databases to start using the web page.

#. Populate locations
To use the countries, states and cities we need to populate the database with this information. The ``populate_locations``
imports the locations from the ``world.sql`` and creates a cache file according to your project to do this task
way faster than the first run.

$ python manage.py populate_locations

.. note::
    That is right, the first time running ``populate_locations`` takes long time as it has to fist sanitize and adapt
    ``world.sql`` to your project. After this a local cached file is created with the same name so subsequents runs
     if any don't have to repeat these processes. Consider drinking a coffee if running without a cached file.
