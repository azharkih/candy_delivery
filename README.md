![Сandy delivery](https://wmpics.pics/di-IJP4.png)
# Сandy delivery

##### интернет-магазин по доставке конфет "Сласти от всех напастей"

### Зависимости
* Python (3.6)
* [Django](https://www.djangoproject.com/) (3.1.7) -- свободный фреймворк 
  для веб-приложений на языке Python, использующий шаблон проектирования MVC.
* [djangorestframework](https://www.django-rest-framework.org/) (3.12.2) - 
инструмент для построения Web API.
* [dynaconf](https://www.dynaconf.com/) (3.1.3) - расширение Django для 
  управления настройками.
* [psycopg2](https://www.psycopg.org/) (2.8.6) - Python-PostgreSQL адаптер 
  баз данных.
* [python-dateutil](https://dateutil.readthedocs.io/en/stable/) (2.8.1) - 
  расширение для стандартного модуля datetime для управления датами.
  
### Организация настроек проекта
Изменяемые настройки проекта находятся в каталоге candy_delivery/config/. В 
файле ".secrets.yaml" хранятся чувствительные настройки проекта, в файле 
settings.yaml - остальные настройки.Каждый из файлов настроек имеет 3 секции: 
default, development, product. Секции development, product соответствуют 
режимам запуска сервиса. В секции default определены настройки по умолчанию для
каждой из секций.
Настройки также могут быть определены в файле .env расположенном в каталоге с 
файлом проекта manage.py или в переменных окружения системы.\
Приоритет настроек в порядке возрастания:
settings.yaml -> .secrets.yaml -> .env -> ENV VARS

По умолчанию проект находится в режиме development. Для перевода в режим 
product необходимо указать это значение в переменной окружения 
`ENV_FOR_DYNACONF = product`

###### Изменяемые настройки, по умолчанию:
```
  SECRET_KEY: ""
  DEBUG: true
  ALLOWED_HOSTS: []
  CORS_ALLOWED_ORIGINS: []
  DATABASE_URL: ""
  IS_NEW_REGIONS_AND_TIME_INTERVALS_AVAILABLE: true
```

### Установка, развертывание и запуск сервиса 
Устанавливаем файлы разработки Python для построения сервера Gunicorn, 
СУБД Postgres и необходимые для взаимодействия с ней библиотеки, а также 
веб-сервер Nginx.
```
sudo apt update
sudo apt install python3-pip python3-dev libpq-dev postgresql postgresql-contrib nginx curl
```
##### Создание базы данных и пользователя PostgreSQL
В интерактивном режиме postgres создаем базу и пользователя и устанавливаем 
параметры подключения пользователя в соответствии с 
[рекомендациями Django](https://docs.djangoproject.com/en/3.0/ref/databases/#optimizing-postgresql-s-configuration). 
Для пользователя необходимо указать безопасный пароль.
```
sudo -u postgres psql
postgres=# CREATE DATABASE candy_delivery;
postgres=# CREATE USER candy_user WITH PASSWORD 'safe_password';
postgres=# ALTER ROLE candy_user SET client_encoding TO 'utf8';
postgres=# ALTER ROLE candy_user SET default_transaction_isolation TO 'read committed';
postgres=# ALTER ROLE candy_user SET timezone TO 'UTC';
postgres=# GRANT ALL PRIVILEGES ON DATABASE candy_delivery TO candy_user;
postgres=# ALTER USER candy_user CREATEDB;
postgres=# \q

```
##### Установка проекта
Настроим права на каталог /var/www
```
sudo chown -R www-data:www-data /var/www
sudo usermod -aG www-data entrant
sudo chmod go-rwx /var/www
sudo chmod go+x /var/www
sudo chgrp -R www-data /var/www
sudo chmod -R go-rwx /var/www
sudo chmod -R g+rwx /var/www
```
Скачиваем с GitHub проект
```
cd /var/www
sudo git clone https://github.com/azharkih/candy_delivery
```
##### Создание виртуального хранилища
Переходим в каталог проекта и создаем виртуальное хранилище
```
cd candy_delivery/
python3 -m venv env #Cоздание виртуального окружения с именем env
source env/bin/activate # активация виртуального хранилища
pip install -r requirements.txt #Установка зависимостей из файла requirements
```
##### Настройка проекта
В каталоге candy_delivery/config/ создаем конфигурационный файл с секретными 
настройками .secrets.yaml
```
product:
  SECRET_KEY: "<safe-secret-key>"
  DATABASE_URL: "postgresql://candy_user:<safe-password>@localhost:5432/candy_delivery"
```
По-умолчанию сервис поддерживает найм курьеров и прием заказов в новых для 
сервиса районах. Если требуется проверка на то, что курьеры и заказы 
принимаются, только в рамках имеющихся в базе кодов регионов и интервалов 
времени необходимо в файле с настроек candy_delivery/config/settings.yaml 
произвести следующую настройку:
```
product:
  ...
  IS_NEW_REGIONS_AND_TIME_INTERVALS_AVAILABLE: false
```  
В каталоге candy_delivery/ создаем файл `.env` с настройками окружения и задаем
режим работы сервиса `product`: 
```
ENV_FOR_DYNACONF = product
```
Перед запуском собираем статические файлы и выполняем миграцию БД:
```
python3 manage.py collectstatic
python3 manage.py migrate 
```
##### Запуск сервиса
Для запуска сервиса в каталоге проекта выполняем команду:
```
python3 manage.py runserver 0.0.0.0:8080
```
### Запуск тестов
Для запуска тестов в каталоге проекта выполняем команду:
```
python3 manage.py test
```
Предусмотрены следующие проверки:
* **Дымный тест всех эндпоинтов.** Проверяется, что при запросе с разрешенными 
  методами для каждого эндпоинта ответ имеет один из статусов 2ХХ, для 
  неразрешенных -- 4ХХ.
  
* **Тест курьерской службы.** Проверка работы обработчиков на эндпоинтах 
  связанных с данными о курьерах.
  * Тест обработки запроса POST /couriers с валидными данными.
    * При валидной структуре json на входе получаем статус ответа 201
    * На выходе получаем json c корректной структурой
    * Проверка, что все данные запроса сохраняются в базе
  * Тест обработки запроса POST /couriers с невалидными данными.
    * При невалидной структуре json на входе получаем статус ответа 400
    * На выходе получаем json c корректной структурой
    * Есть проверка на обязательные поля
    * При получении неописанного поля -- возвращается ошибка
    * Валидация входных данных
    * При запросе с невалидными данными в базу ничего не пишется.
  * Тест обработки запроса PATCH /couriers/$courier_id с валидными данными.
    * При валидной структуре json на входе получаем статус ответа 200
    * Доступны для редактирования поля courier_type, regions, working_hours
      в любой комбинации.
    * На выходе получаем json c корректной структурой
    * Все данные запроса сохраняются в базе
    * После изменения курьера снялись заказы которые он не может доставить
  * Тест обработки запроса PATCH /couriers/$courier_id с невалидными данными.
    * Поле courier_id заблокировано от изменений
    * При получении неописанного поля -- возвращается ошибка
    * Валидация входных данных.
  * Тест обработки запроса GET /couriers/$courier_id.
    * При отправке запроса на эндпоинт с id существующего курьера получаем 
      ответ со статусом 200. 
    * Структура ответа для курьера не совершившего ни одной доставки
    * Структура ответа для курьера с завершенными доставками
    * Корректность расчета рейтинга
    * Корректность расчета заработка
    * Корректность расчета заработка при смене типа курьера в середине 
      развоза.
    
* **Тест службы обработки заказов.** Проверка работы обработчиков на эндпоинтах 
  связанных с заказами.
  * Тест обработки запроса POST /orders с валидными данными.
    * При валидной структуре json на входе получаем статус ответа 201
    * На выходе получаем json c корректной структурой
    * Проверка, что все данные запроса сохраняются в базе
  * Тест обработки запроса POST /orders с невалидными данными.
    * При невалидной структуре json на входе получаем статус ответа 400
    * На выходе получаем json c корректной структурой
    * Есть проверка на обязательные поля
    * При получении неописанного поля -- возвращается ошибка
    * Валидация входных данных
    * При запросе с невалидными данными в базу ничего не пишется.
  * Тест обработки запроса POST /orders/assign с валидными данными.
    * При валидной структуре json на входе получаем статус ответа 200
    * Корректность структуры ответа, для курьера с активным развозом, с 
      завершенным развозом с доступными заказами и их отсутствием
    * Проверяем, что заказы назначены c максимально возможной комбинацией 
      весов и не превышают грузоподъемность курьера.
    * Обработчик идемпотентен
    * Доставленные заказы текущего развоза исключаются, а время остается 
      тоже.
  * Тест обработки запроса POST /orders/assign с невалидными данными.
    * При невалидной структуре json на входе получаем статус ответа 400
  * Тест обработки запроса POST /orders/complete с валидными данными.
    * При валидной структуре json на входе получаем статус ответа 200
    * Корректность структуры ответа
    * Обработчик идемпотентен
    * Время завершения заказа устанавливется верно и корректно считается 
      время доставки.
  * Тест обработки запроса POST /orders/complete с невалидными данными.
    * Если заказ не найден возвращается ошибка 400
    * Если заказ назначен на другого курьера возвращается ошибка 400
    * Если заказ не назначен возвращается ошибка 400

### Настройка gunicorn
Проверяем работу Gunicorn:
```
gunicorn --bind 0.0.0.0:8080 candy_delivery.wsgi
```
Откроем для настройки
```
sudo nano /etc/systemd/system/gunicorn.socket
```
Пропишем в файле несколько настроек:
```
[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/run/gunicorn.sock

[Install]
WantedBy=sockets.target
```
Откроем служебный файл systemd для настройки работы сервиса:
```
sudo nano /etc/systemd/system/gunicorn.service
```
```
[Unit]
Description=gunicorn daemon
Requires=gunicorn.socket
After=network.target

[Service]
User=entrant
Group=www-data
WorkingDirectory=/var/www/candy_delivery
ExecStart=/var/www/candy_delivery/env/bin/gunicorn \
          --access-logfile - \
          --workers 5 \
          --bind unix:/run/gunicorn.sock \
          candy_delivery.wsgi:application

[Install]
WantedBy=multi-user.target
```
Запускаем и активируем сокет Gunicorn
```
sudo systemctl start gunicorn.socket
sudo systemctl enable gunicorn.socket
```
Тестируем:
```
sudo systemctl status gunicorn.socket
file /run/gunicorn.sock
```
Установим соединение с сокетом через curl.
```
curl --unix-socket /run/gunicorn.sock localhost
```
Перезапускаем процессы Gunicorn
```
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
```

### Настройка NGINX
Откроем для настройки
```
sudo nano /etc/nginx/sites-available/candy_delivery
```
```
server {
    listen 80;
    server_name 130.193.56.231;

    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        alias /var/www/candy_delivery/static/;
    }

    location /media/ {
        alias /var/www/candy_delivery/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
    }
}
```
Теперь мы можем активировать файл, привязав его к каталогу sites-enabled:
```
sudo ln -s /etc/nginx/sites-available/candy_delivery /etc/nginx/sites-enabled
```
Протестируем:
```
sudo nginx -t
```
Если ошибок нет, то перезапускаем сервер и даём брандмауэру необходимые права:
```
sudo systemctl restart nginx
sudo ufw allow 'Nginx Full'
```
