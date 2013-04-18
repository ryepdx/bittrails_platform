#!/bin/bash
cd ..
sudo apt-get -y install python2.7 git python-setuptools gcc python-dev
git clone https://github.com/ryepdx/bittrails_platform_site-packages.git
mv bittrails_platform_site-packages /usr/lib/python2.7/site-packages
cd bittrails_platform
sudo easy_install pip
sudo pip install -r requirements.txt
sudo pip install iso8601 nose pytz pymongo
cd ..
sudo sh -c 'echo "deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen" > /etc/apt/sources.list.d/10gen.list'
wget http://nginx.org/keys/nginx_signing.key
sudo apt-key add nginx_signing.key
rm nginx_signing.key
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv 7F0CEB10
sudo apt-get -y update
sudo apt-get -y install nginx
sudo pip install uwsgi
sudo useradd -c 'uwsgi user,,,' -g nginx -d /nonexistent -s /bin/false uwsgi
sudo sh -c 'echo "description \"uWSGI\"\n" > /etc/init/uwsgi.conf'
sudo sh -c 'echo "start on runlevel [2345]\n" >> /etc/init/uwsgi.conf'
sudo sh -c 'echo "stop on runlevel [06]\n\n" >> /etc/init/uwsgi.conf'
sudo sh -c 'echo "respawn\n\n" >> /etc/init/uwsgi.conf'
sudo sh -c 'echo "exec uwsgi --master --processes 4 --die-on-term --uid uwsgi --gid nginx --socket /tmp/uwsgi.sock --chmod-socket 660 --no-site --vhost --logto /var/log/uwsgi.log" >> /etc/init/uwsgi.conf'
sudo apt-get install mongodb-10gen
cd bittrails_platform
echo "DEBUG=True" > settings_local.py
echo "y" | python . --no-server --reset-db
python -m async_tasks.datastreams.fill_zeroes
cd ..
