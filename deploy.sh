#!/bin/env bash

mkdir -p logs

apt install -y nginx python3.12 python3-pip docker.io supervisor

python3 -m venv venv

source venv/bin/activate

pip3 install .

cp frontend/* /var/www/html/.

rm -i /etc/ngin/sites-enabled/default

deactivate

docker run -d --name redis-server -p 127.0.0.1:6379:6379 redis:7.2.5

CURRENT_DIRECTORY=`pwd`

sed -i "s|__DIR_MACRO__|${CURRENT_DIRECTORY}|" supervisord/deps_visionary.conf

cp supervisord/deps_visionary.conf /etc/supervisor/conf.d/.

supervisorctl update

supervisorctl restart all
