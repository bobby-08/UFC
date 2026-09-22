FROM apache/airflow:3.3.1

USER root

# Playwright browsers are shared by all Airflow services and installed into a
# location readable by the airflow user.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

COPY requirements-app.txt /tmp/requirements-app.txt

USER airflow
RUN pip install --no-cache-dir -r /tmp/requirements-app.txt

USER root
RUN playwright install --with-deps chromium \
    && chown -R airflow:root /ms-playwright

USER airflow
