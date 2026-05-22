FROM apache/superset:4.0.0

USER root

RUN pip install --no-cache-dir \
    psycopg2-binary \
    redis

COPY superset_config.py /app/pythonpath/superset_config.py

COPY docker-init.sh /docker-init.sh
RUN chmod +x /docker-init.sh

USER superset

CMD ["/docker-init.sh"]