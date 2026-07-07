FROM python:3.11-slim

WORKDIR /app

RUN adduser --disabled-password --gecos "" myuser

USER myuser

ENV PATH="/home/myuser/.local/bin:$PATH"
ENV PYTHONUNBUFFERED=1

COPY --chown=myuser:myuser requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=myuser:myuser . .

EXPOSE 8080

CMD adk run --port=8080 --host=0.0.0.0 --no-use_local_storage /app
