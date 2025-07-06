FROM python:3.11-slim

ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

WORKDIR /app

COPY ./whazzastream /app
COPY requirements.txt /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5015

CMD ["python", "app.py"]
