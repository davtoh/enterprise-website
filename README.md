WEB PAGE DOCUMENTATION:
=======================


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

### Installing requirements
$ pip install requirements.txt

### Additional resources and databases
Download the following resources, extract and place them on the working directory

* [world.sql](https://github.com/prograhammer/countries-regions-cities)
* [GeoLiteCity.dat](http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz)
* [GeoLiteCityv6.dat](http://geolite.maxmind.com/download/geoip/database/GeoLiteCityv6-beta/GeoLiteCityv6.dat.gz)

### Run migrations
$ python manage.py makemigrations
$ python manage.py migrate

### Create admin user
$ python manage.py createsuperuser --username=admin --email=email@messages.com

### (DEBUG) Create debug users
$ python manage.py populate_users --test

### Populate countries, states and cities
$ python manage.py populate_locations
