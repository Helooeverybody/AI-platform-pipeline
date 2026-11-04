FROM python:3.12-slim

ARG GIT_SHA=unknown
LABEL org.opencontainers.image.revision=$GIT_SHA

WORKDIR /app
COPY pyproject.toml .
COPY src/ ./src/
COPY examples/ ./examples/
RUN python -m pip install --no-cache-dir '.[ml]'

CMD ["python", "-c", "print('hello from a job')"]
