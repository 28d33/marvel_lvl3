# Task 7 - backend image for the Level 0 web application.
#
# Built with the jenkins/app directory as the build context so that the
# application source can be copied in, rather than mounted from the host:
#
#   docker build -f task_docker/backend/Dockerfile -t marvel-pm-backend:lvl3 jenkins/app
#
# The difference from the Task 2 image is deliberate. Task 2 bind-mounted
# ./backend over /var/www/html for live reload during Jenkins testing. Here the
# source is baked into a layer, which is what "Dockerize" actually means, and
# it makes the contrast with a bind mount visible (see the report).

FROM php:8.2-apache

# pdo_mysql is what the application actually uses - src/Db.php opens a PDO
# connection - and mysqli is kept because the MySQL client utilities in this
# image expect it. a2enmod rewrite is required by the front controller.
RUN docker-php-ext-install pdo_mysql mysqli \
 && a2enmod rewrite

WORKDIR /var/www/html

# Copied in one instruction so that the application source is a single layer.
COPY backend/ /var/www/html/

# The front controller lives in public/; everything else is application code
# that must not be web reachable.
RUN sed -i 's!/var/www/html!/var/www/html/public!g' /etc/apache2/sites-available/000-default.conf \
 && printf '<Directory /var/www/html/public>\n    AllowOverride All\n</Directory>\n' \
      >> /etc/apache2/sites-available/000-default.conf

EXPOSE 80

# Without a compose file there is no depends_on with a condition, so the health
# check is the signal used to decide when the backend is ready to serve.
#
# The check deliberately omits curl's -f flag. GET /api/vaults answers 401
# Unauthorized until a session exists, and -f treats any 4xx as a failure, so
# with -f this container would report unhealthy forever. Without -f, curl exits
# 0 for any HTTP response, which is exactly the question being asked here: has
# Apache started and is PHP routing requests? A connection refused still fails.
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=5 \
  CMD curl -sS -o /dev/null http://localhost/api/vaults || exit 1