# Copyright (C) 2020 Nokia

FROM python:3.8.0-alpine3.10
RUN apk add --no-cache \
        openssh \
        openssh-sftp-server \
        bash \
        sudo && \
    mkdir -p /var/run/sshd && \
    echo 'root:targetpassword' | chpasswd && \
    echo 'PermitRootLogin yes' >>  /etc/ssh/sshd_config && \
    ssh-keygen -f /etc/ssh/ssh_host_rsa_key -N '' -t rsa && \
    ssh-keygen -f /root/.ssh/id_rsa -t rsa -N '' && \
    cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys && \
    chmod og-wx /root/.ssh/authorized_keys
EXPOSE 22
RUN unlink /usr/local/bin/python
CMD ["/usr/sbin/sshd", "-D"]

