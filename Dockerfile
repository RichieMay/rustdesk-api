# AlpineLinux 3.15.0 with rustdesk-api
FROM alpine:3.15.0
MAINTAINER RichieMay mayboe@gmail.com

# Set useful environment variables
ENV LANG                en_US.UTF-8
ENV LC_ALL              en_US.UTF-8
ENV LANGUAGE            en_US.UTF-8
ENV ALPINE_OS_VERSION   3.15.0

# Change repositories in china
RUN echo "http://mirrors.ustc.edu.cn/alpine/v3.15/main" > "/etc/apk/repositories" && \
    echo "http://mirrors.ustc.edu.cn/alpine/v3.15/community" >> "/etc/apk/repositories"

# Install helper tools and python3
RUN mkdir -p /data /usr/share/rustdesk-api && \
    apk add --no-cache bash curl python3 py3-flask py3-sqlalchemy

# Expose default HTTP connector port.
EXPOSE 80

# Add python script file
ADD api.py /usr/share/rustdesk-api/api.py
ADD database_manager.py /usr/share/rustdesk-api/database_manager.py

# Setting startup file
ENTRYPOINT ["/usr/bin/python3", "/usr/share/rustdesk-api/api.py"]