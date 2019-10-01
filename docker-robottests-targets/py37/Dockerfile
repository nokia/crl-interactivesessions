# Copyright (C) 2019, Nokia

FROM python:3.7.4
RUN apt-get update && \
    apt-get install -y openssh-server && \
    mkdir -p /var/run/sshd && \
    echo 'root:targetpassword' | chpasswd && \
    echo 'PermitRootLogin yes' >>  /etc/ssh/sshd_config
EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]
