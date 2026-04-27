FROM python:3.12-slim

RUN apt-get update && apt-get install -y g++ && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --shell /usr/sbin/nologin judgeuser

WORKDIR /app
RUN chown -R judgeuser:judgeuser /app

USER judgeuser
