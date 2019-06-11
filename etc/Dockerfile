FROM 	fedora:29
RUN 	dnf -y install git \
	    patch \
	    make \
	    gcc \
	    findutils \
	    bzip2 \
	    bzip2-devel \
	    readline-devel \
	    openssh-server \
        procps \
	    sqlite \
	    sqlite-devel \
	    openssl-devel \
	    tk-devel \
	    libffi-devel \
	    python2 \
	    python3 \
	    python3-virtualenv \
	    tox \
	    python-pip
RUN	    dnf -y install passwd
RUN     dnf -y install sudo
RUN	    virtualenv -p python3 /tmp/pyenv3
RUN	    virtualenv -p python2 /tmp/pyenv2
RUN	    useradd python2user -m && useradd python3user -m \
	    && mkdir /home/python2user/.ssh \
	    && mkdir /home/python3user/.ssh \
	    && ssh-keygen -f /root/.ssh/id_rsa -P "" \
	    && cp ~/.ssh/id_rsa.pub /home/python2user/.ssh/authorized_keys \
	    && cp ~/.ssh/id_rsa.pub /home/python3user/.ssh/authorized_keys
RUN	    passwd python2user --stdin <<< "python2testing" \
	    && passwd python3user --stdin <<< "python3testing"
RUN	    echo source /tmp/pyenv2/bin/activate >> /home/python2user/.bashrc
RUN	    echo source /tmp/pyenv3/bin/activate >> /home/python3user/.bashrc
RUN     echo 'python2user   ALL=NOPASSWD: ALL' >> /etc/sudoers.d/python2user
RUN     echo 'python3user   ALL=NOPASSWD: ALL' >> /etc/sudoers.d/python3user
WORKDIR /work
CMD 	etc/docker_cmd
