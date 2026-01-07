# Изначальный образ
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости в рабочую директорию и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код в рабочую директорию
COPY app.py .

# Экспонируем порт
EXPOSE 5000

# Запускаем приложение
CMD ["python", "app.py"]