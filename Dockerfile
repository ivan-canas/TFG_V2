FROM python:3.8.13-alpine3.16

RUN apk add --no-cache --update \
    python3 python3-dev gcc \
    gfortran musl-dev

WORKDIR /app

COPY . /app

RUN pip3 install --upgrade pip setuptools && \
    pip3 install -r requeriments.txt

CMD cd server;source venv/bin/activate;python3 server.py

CMD cd app;npm start


