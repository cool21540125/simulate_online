FROM mysql:5.7
ENV MYSQL_ROOT_PASSWORD 1qaz@WSX
COPY initdb.sql /docker-entrypoint-initdb.d/