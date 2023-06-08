FROM python:3.10
WORKDIR /usr/src/app
COPY . .
RUN pip install -U pip && pip install --no-cache-dir -r requirements.txt
CMD ["python", "Aiogram_bot.py"]
