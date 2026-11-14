
FROM python:3.14-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential gcc libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m pip install --upgrade pip setuptools wheel

# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install h5py separately
RUN pip install --no-cache-dir --pre \
    --extra-index-url https://pypi.anaconda.org/scientific-python-nightly-wheels/simple \
    h5py

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
