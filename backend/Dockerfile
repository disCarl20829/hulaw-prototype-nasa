FROM python:3.14-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       gcc \
       libhdf5-dev \
       pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m pip install --upgrade pip setuptools wheel

# Install the intentionally selected NumPy development release
RUN python -m pip install --no-cache-dir \
    --pre \
    --extra-index-url https://pypi.anaconda.org/scientific-python-nightly-wheels/simple \
    "numpy==2.6.0.dev0"

# Install the remaining dependencies
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]