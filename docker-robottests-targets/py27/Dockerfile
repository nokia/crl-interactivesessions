# Copyright (C) 2019, Nokia

FROM python:2.7.17-alpine3.10
RUN apk add --no-cache \
        openssh \
        openssh-sftp-server \
        bash && \
    mkdir -p /var/run/sshd && \
    echo 'root:targetpassword' | chpasswd && \
    echo 'PermitRootLogin yes' >>  /etc/ssh/sshd_config && \
    ssh-keygen -f /etc/ssh/ssh_host_rsa_key -N '' -t rsa
EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]
