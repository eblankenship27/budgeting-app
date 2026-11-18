FROM public.ecr.aws/lambda/python:3.12

# Copy uv's binary from its official image; pinned to the version you use locally.
COPY --from=ghcr.io/astral-sh/uv:0.11.11 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1

# Dependencies first: this layer is reused from cache until uv.lock changes.
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-emit-project -o requirements.txt && \
    uv pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

COPY app/ ${LAMBDA_TASK_ROOT}/app/
COPY alembic.ini  ${LAMBDA_TASK_ROOT}/
COPY alembic/ ${LAMBDA_TASK_ROOT}/alembic


CMD ["app.main.handler"]