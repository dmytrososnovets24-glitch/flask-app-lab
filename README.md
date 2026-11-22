# Flask: навчальні лабораторні роботи

**Студент:** Сосновець Дмитро Сергійович, КНУ імені Василя Стефаника, ІПЗ-33
**Курс:** Вебпрограмування мовою Python
**Розгорнутий сайт:** https://flask-app-sosnovets.onrender.com/

Кожна лабораторна виконана у власній гілці, кожна наступна створена з попередньої. Гілка `main` містить усі роботи (лаби 1–9) і розгортається на Render.

| Лаба | Тема | Гілка |
|---|---|---|
| 1 | Найпростіший Flask-додаток, venv, Git, розгортання на Render | [`lab1`](../../tree/lab1) |
| 2 | Маршрутизація та шаблони (резюме й контакти) | [`lab2`](../../tree/lab2) |
| 3 | Модульна структура, Blueprints, unittest | [`lab3`](../../tree/lab3) |
| 4 | Сесії та кукі, flash, кольорова схема | [`lab4`](../../tree/lab4) |
| 5 | WTF-форми, TinyDB, CRUD товарів | [`lab5`](../../tree/lab5) |
| 6 | ORM, SQLAlchemy, CRUD постів, міграції | [`lab6`](../../tree/lab6) |
| 7 | Зв'язки, робота з міграціями (Product, Category) | [`lab7`](../../tree/lab7) |
| 8 | ORM, зв'язки між моделями (User, Post, Tag), оптимізація запитів | [`lab8`](../../tree/lab8) |
| 9 | Реєстрація і вхід користувачів, Flask-Bcrypt, Flask-Login | [`lab9`](../../tree/lab9) |

У кожній гілці є власний `README.md` зі звітом і скриншотами.

## Запуск поточної версії
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
flask db upgrade
flask run                                  # http://127.0.0.1:8080
python -m unittest discover tests -v
```

Починаючи з лабораторної №6 застосунок створюється фабрикою `create_app()`, точка входу — `run.py`. На Render: Build Command `pip install -r requirements.txt`, Start Command `flask db upgrade && gunicorn run:app`.

---

## Лабораторна робота №1. Найпростіший Flask-додаток

### Що зроблено
1. Створено каталог проєкту `flask_app_sosnovets` і віртуальне середовище `.venv`; перевірено `pip list`, оновлено `pip`, встановлено Flask (`pip install flask`, `pip show flask` — версія 3.0.3).
2. Ініціалізовано Git-репозиторій, `.gitignore` виключає віртуальне середовище.
3. Файл `app.py` без коментарів:
   ```python
   from flask import Flask
   app = Flask(__name__)

   @app.route('/')
   def main():
       return 'Hello, world!'

   if __name__ == '__main__':
       app.run(debug=True)
   ```
4. Запуск `python app.py` (порт 5000) і `flask run`; режим debug вмикається через `.flaskenv` (`FLASK_DEBUG=1`, `FLASK_APP=app.py`, `FLASK_RUN_PORT=8080`) за допомогою `python-dotenv`.
5. Створено `requirements.txt` (Flask, python-dotenv, gunicorn), коміти й репозиторій `flask-app-lab` на GitHub.
6. Розгортання на Render.com: Build Command `pip install -r requirements.txt`, Start Command `gunicorn app:app`, тариф Free, гілка `main`.

### Скриншоти
**Розгортання на Render завершено (Deploy succeeded)**
![Deploy](screenshots/lab1/03_render_deploy_succeeded.jpg)

**Налаштування сервісу на Render**
![Налаштування сервісу](screenshots/lab1/04_render_service_settings.jpg)

**Репозиторій на GitHub**
![GitHub](screenshots/lab1/05_github_repo.jpg)

**Дашборд Render: список сервісів**
![Дашборд, сервіси](screenshots/lab1/06_render_dashboard_services.jpg)

**Дашборд Render: огляд проєктів**
![Дашборд, огляд](screenshots/lab1/06a_render_dashboard_overview.jpg)
