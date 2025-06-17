# Using python
FROM python:3.13.1-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

EXPOSE 8050

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8050", "--timeout", "300", "app:server"]
