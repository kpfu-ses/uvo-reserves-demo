FROM python:3.6-alpine

RUN adduser -D uvo-reserves

WORKDIR /home/uvo-reserves

COPY requirements.txt requirements.txt
RUN python -m venv venv
RUN apk add libc-dev
RUN apk add build-base
RUN pip install -U pip
RUN venv/bin/pip install -r requirements.txt
RUN venv/bin/pip install gunicorn


COPY app app
COPY migrations migrations
COPY app.py config.py boot.sh ./
RUN chmod +x boot.sh

ENV FLASK_APP app.py

RUN chown -R uvo-reserves:uvo-reserves ./
USER uvo-reserves


EXPOSE 5000
ENTRYPOINT ["./boot.sh"]