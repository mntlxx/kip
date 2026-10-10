#!/bin/bash
echo "[*] Создание виртуального окружения..."
python3 -m venv venv

echo "[*] Активация окружения и установка зависимостей..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[✓] Установка завершена! Для запуска используйте: source venv/bin/activate && python main.py"