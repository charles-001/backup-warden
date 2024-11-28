FROM python:alpine

RUN apk --no-cache add curl
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$PATH:/root/.local/bin"

WORKDIR /app
COPY poetry.lock pyproject.toml ./
COPY . /app
RUN poetry install

ENTRYPOINT ["poetry", "run", "backup-warden"]
CMD ["--help"]
