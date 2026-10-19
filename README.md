# Книжная полка — версия с PostgreSQL и pgAdmin

Учебный сайт-каталог книг. Эта версия использует PostgreSQL, поэтому таблицу `books` можно просматривать и редактировать в pgAdmin.

## 1. Установить PostgreSQL

Установите PostgreSQL и pgAdmin. В установщике запомните пароль пользователя `postgres`. pgAdmin — это программа управления; сам сервер PostgreSQL тоже должен быть установлен и запущен.

## 2. Создать базу в pgAdmin

1. Откройте pgAdmin и подключитесь к локальному серверу PostgreSQL (пароль пользователя `postgres`).
2. В дереве слева нажмите правой кнопкой на `Databases` → `Create` → `Database…`.
3. Имя базы: `library_db`; владельца оставьте `postgres`; нажмите `Save`.
4. Выберите `library_db`, откройте `Tools` → `Query Tool`.
5. Откройте файл `schema.sql`, скопируйте его содержимое в Query Tool и нажмите Execute (▶). Будет создана таблица `books`. Приложение также создаёт её само при первом запуске, но этот шаг удобен, чтобы увидеть таблицу в pgAdmin.

## 3. Настроить проект

1. Убедитесь, что установлен Python 3.
2. В папке проекта скопируйте `.env.example` в новый файл с именем `.env`.
3. Откройте `.env` и замените `CHANGE_ME` на пароль пользователя `postgres`, установленный вами при установке PostgreSQL. Если имя пользователя/базы/порт отличаются, измените и их.
4. Откройте терминал в этой папке и выполните:

   ```powershell
   python -m pip install -r requirements.txt
   python app.py
   ```

5. Откройте <http://127.0.0.1:8000>.

Если вы хотите перенести свои записи из прежней SQLite-базы `library.db`, выполните перед запуском сайта (или после — также можно) команду:

```powershell
python migrate_sqlite_to_postgres.py
```

Скрипт добавит в PostgreSQL книги, которых там ещё нет по сочетанию названия и автора.

`npm install` не требуется: сайт написан на Python, а не на Node.js.

## 4. Где увидеть таблицу в pgAdmin

После запуска сайта в pgAdmin обновите дерево: `Servers` → ваш сервер → `Databases` → `library_db` → `Schemas` → `public` → `Tables`. Нажмите правой кнопкой на `books` → `View/Edit Data` → `All Rows`.

При первом запуске сайт автоматически создаёт таблицу и пять демонстрационных книг, если таблица пустая. Книги, которые добавляете на сайте, хранятся в PostgreSQL и будут видны в pgAdmin.

## Частые проблемы

- `connection refused` / не удалось подключиться: проверьте, что служба PostgreSQL запущена и порт равен `5432`.
- `password authentication failed`: исправьте `DB_PASSWORD` в `.env`.
- `database "library_db" does not exist`: создайте базу через pgAdmin, как в шаге 2.
- `No module named psycopg`: выполните `python -m pip install -r requirements.txt`.
