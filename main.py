# main.py

from threading import Thread
from bot import get_app
from web import app as flask_app


def run_flask():
    flask_app.run(port=5000)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    application = get_app()
    application.run_polling()