@echo off
echo [*] Создание виртуального окружения...
python -m venv venv

echo [*] Активация окружения и установка зависимостей...
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo [✓] Установка завершена! Для запуска используйте: venv\Scripts\activate && python main.py
pause