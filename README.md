WEB PAGE DOCUMENTATION:
=======================


# INSTALLATION INSTRUCTIONS:

## ON LINUX:
### Install Mysql
instructions from https://www.digitalocean.com/community/tutorials/how-to-install-mysql-on-ubuntu-18-04
$ sudo apt update
$ sudo apt install mysql-server
$ sudo mysql_secure_installation

### to allow phpMyAdmin
$ sudo mysql
mysql> SELECT user,authentication_string,plugin,host FROM mysql.user;
mysql> ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'password';
mysql> FLUSH PRIVILEGES;
mysql> SELECT user,authentication_string,plugin,host FROM mysql.user;
mysql> exit

### add user for database
$ mysql -u root -p
mysql> CREATE DATABASE productsDB;
mysql> CREATE USER 'user'@'localhost' IDENTIFIED BY 'Somepass123.';
mysql> GRANT ALL PRIVILEGES ON productsDB.* TO 'user'@'localhost' WITH GRANT OPTION;
mysql> exit

### install python requirements
Install Requirement.txt

### run migrations
$ python manage.py migrate

### create admin user
$ python manage.py createsuperuser --username=admin --email=email@messages.com
