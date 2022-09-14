#!/bin/bash
#
# Edit these:
# The main part of your domain (mydomain.com)
ROOT_DOMAIN=nativeplanet.live
# A strong random password (you won't need to use it)
HEADER_AUTH=asdasdasd
# A strong random password (you will need to remember it)
REG_CODE=dsadsadas
# Path to the SSH key for your VPS
SSH_KEY="~/.ssh/key.pem"


# Don't edit below
######
chmod 600 ${SSH_KEY}
SSH_PUB=`ssh-keygen -f ${SSH_KEY} -y`
printf "[relay]\nrelay.${ROOT_DOMAIN}\n\n[relay:vars]\nansible_user=\"root\"\nansible_ssh_private_key_file=${SSH_KEY}" > hosts
ssh-keyscan -H relay.${ROOT_DOMAIN} >> ~/.ssh/known_hosts
ssh -i ${SSH_KEY} -o "StrictHostKeyChecking=no" \
        root@relay.${ROOT_DOMAIN} "sed -i 's@PasswordAuthentication yes@PasswordAuthentication no@g' /etc/ssh/sshd_config"
ssh -i ${SSH_KEY} -o "StrictHostKeyChecking=no" \
        root@relay.${ROOT_DOMAIN} "systemctl restart sshd"
ssh -i ${SSH_KEY} root@relay.${ROOT_DOMAIN} \
        "echo \"${SSH_PUB}\" >> /home/ubuntu/.ssh/authorized_keys && echo \"${SSH_PUB}\" >> ~/.ssh/authorized_keys"
ansible-playbook --key-file ${SSH_KEY} \
    -i ./hosts -e "ROOT_DOMAIN=${ROOT_DOMAIN} \
    HEADER_AUTH=${HEADER_AUTH} REG_CODE=${REG_CODE}\
    ansible_python_interpreter=$(which python3)" \
    ./relay.yml