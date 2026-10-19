"""Мини-сайт «Книжная полка» на Python и PostgreSQL."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import html
import os
import psycopg
from psycopg.rows import dict_row

BASE_DIR = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8000

SAMPLE_BOOKS = [
    ("Маленький принц", "Антуан де Сент-Экзюпери", 1943, "Сказка"),
    ("Преступление и наказание", "Фёдор Достоевский", 1866, "Роман"),
    ("451° по Фаренгейту", "Рэй Брэдбери", 1953, "Фантастика"),
    ("Приключения Тома Сойера", "Марк Твен", 1876, "Приключения"),
    ("Хоббит", "Дж. Р. Р. Толкин", 1937, "Фэнтези"),
]


def load_local_env():
    """Загружает настройки из .env без установки дополнительной библиотеки."""
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def connect_db():
    """Подключается к PostgreSQL с параметрами из файла .env или окружения."""
    load_local_env()
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "library_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "CHANGE_ME"),
        row_factory=dict_row,
    )


def init_db():
    """Создаёт таблицу PostgreSQL и добавляет книги, если таблица пустая."""
    with connect_db() as connection:
        schema = (BASE_DIR / "schema.sql").read_text(encoding="utf-8")
        connection.execute(schema)
        count = connection.execute("SELECT COUNT(*) AS count FROM books").fetchone()["count"]
        if count == 0:
            connection.cursor().executemany(
                "INSERT INTO books (title, author, year, genre) VALUES (%s, %s, %s, %s)",
                SAMPLE_BOOKS,
            )


def escape(value):
    return html.escape("" if value is None else str(value), quote=True)


def render_book_rows(rows):
    if not rows:
        return '<tr><td colspan="5" class="empty">По вашему запросу ничего не найдено.</td></tr>'
    result = []
    for book in rows:
        year = escape(book["year"]) if book["year"] is not None else "—"
        result.append(
            "<tr>"
            f"<td class=\"book-title\">{escape(book['title'])}</td>"
            f"<td>{escape(book['author'])}</td>"
            f"<td>{year}</td>"
            f"<td><span class=\"tag\">{escape(book['genre'])}</span></td>"
            "<td class=\"action-cell\"><form method=\"post\" action=\"/delete\" "
            "onsubmit=\"return confirm('Удалить эту книгу?')\">"
            f"<input type=\"hidden\" name=\"id\" value=\"{int(book['id'])}\">"
            "<button class=\"delete-btn\" type=\"submit\" aria-label=\"Удалить книгу\">Удалить</button>"
            "</form></td></tr>"
        )
    return "\n".join(result)


class LibraryHandler(BaseHTTPRequestHandler):
    def send_text(self, text, content_type="text/html; charset=utf-8", status=200):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def redirect_home(self):
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/style.css":
            css_path = BASE_DIR / "static" / "style.css"
            self.send_text(css_path.read_text(encoding="utf-8"), "text/css; charset=utf-8")
            return
        if parsed.path not in ("/", "/index.html"):
            self.send_text("<h1>404 — страница не найдена</h1><p><a href='/'>На главную</a></p>", status=404)
            return

        params = parse_qs(parsed.query)
        query = params.get("q", [""])[0].strip()
        with connect_db() as connection:
            if query:
                pattern = f"%{query}%"
                books = connection.execute(
                    "SELECT id, title, author, year, genre FROM books "
                    "WHERE title ILIKE %s OR author ILIKE %s OR genre ILIKE %s ORDER BY title",
                    (pattern, pattern, pattern),
                ).fetchall()
            else:
                books = connection.execute(
                    "SELECT id, title, author, year, genre FROM books ORDER BY title"
                ).fetchall()
            total = connection.execute("SELECT COUNT(*) AS count FROM books").fetchone()["count"]

        template = (BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")
        page = template.replace("{{BOOK_ROWS}}", render_book_rows(books))
        page = page.replace("{{QUERY}}", escape(query))
        page = page.replace("{{COUNT}}", str(total))
        page = page.replace("{{FOUND}}", str(len(books)))
        self.send_text(page)

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(min(length, 100_000)).decode("utf-8", errors="replace")
        form = parse_qs(raw, keep_blank_values=True)

        if parsed.path == "/add":
            title = form.get("title", [""])[0].strip()
            author = form.get("author", [""])[0].strip()
            year_text = form.get("year", [""])[0].strip()
            genre = form.get("genre", [""])[0].strip() or "Без жанра"
            if not title or not author or len(title) > 150 or len(author) > 120 or len(genre) > 60:
                self.send_text(
                    "<h1>Проверьте данные</h1><p>Название и автор обязательны; проверьте длину полей.</p>"
                    "<p><a href='/'>Вернуться на сайт</a></p>", status=400
                )
                return
            year = None
            if year_text:
                try:
                    year = int(year_text)
                    if year < 1 or year > 2100:
                        raise ValueError
                except ValueError:
                    self.send_text(
                        "<h1>Некорректный год</h1><p>Введите год от 1 до 2100.</p>"
                        "<p><a href='/'>Вернуться на сайт</a></p>", status=400
                    )
                    return
            with connect_db() as connection:
                connection.execute(
                    "INSERT INTO books (title, author, year, genre) VALUES (%s, %s, %s, %s)",
                    (title, author, year, genre),
                )
            self.redirect_home()
            return

        if parsed.path == "/delete":
            try:
                book_id = int(form.get("id", [""])[0])
            except ValueError:
                self.send_text("<h1>Некорректный ID</h1><p><a href='/'>На главную</a></p>", status=400)
                return
            with connect_db() as connection:
                connection.execute("DELETE FROM books WHERE id = %s", (book_id,))
            self.redirect_home()
            return

        self.send_text("<h1>404 — действие не найдено</h1><p><a href='/'>На главную</a></p>", status=404)

    def log_message(self, format_string, *args):
        # Сохраняем стандартные короткие сообщения доступа в терминале.
        super().log_message(format_string, *args)


def main():
    init_db()
    server = HTTPServer((HOST, PORT), LibraryHandler)
    print("Книжная полка запущена: http://127.0.0.1:8000")
    print("Для остановки нажмите Ctrl+C.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
