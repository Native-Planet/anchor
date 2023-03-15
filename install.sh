#!/bin/bash
######
# Don't edit below
######
source ./settings.sh
HEADER_AUTH=$(openssl rand -hex 20)
if grep -Fxq "CHANGE_ME!" settings.sh
then
    echo "Please edit settings.sh with your settings"
    exit 1
fi
if command -v apt &> /dev/null
then
    sudo apt update && sudo apt install -y python3 ansible
elif ! command -v apt &> /dev/null
then
    if ! command -v python3 &> /dev/null
        then
        echo "Please install Python 3"
        exit 1
    elif ! command -v ansible-playbook &> /dev/null
        then
        echo "Please install Ansible"
        exit 1
    fi
fi
host -t A anchor.${ROOT_DOMAIN} | grep "has address" >/dev/null ||     {
    echo "no DNS records for anchor.${ROOT_DOMAIN}!"
    exit 1
}
chmod 600 ${SSH_KEY}
mkdir -p ~/.ssh
SSH_PUB=`ssh-keygen -f ${SSH_KEY} -y`
printf "[anchor]\nanchor.${ROOT_DOMAIN}\n\n[anchor:vars]\nansible_user=\"root\"\nansible_ssh_private_key_file=${SSH_KEY}" > hosts
ssh-keyscan -H anchor.${ROOT_DOMAIN} >> ~/.ssh/known_hosts
ssh -i ${SSH_KEY} -o "StrictHostKeyChecking=no" \
        root@anchor.${ROOT_DOMAIN} "sed -i 's@PasswordAuthentication yes@PasswordAuthentication no@g' /etc/ssh/sshd_config"
ssh -i ${SSH_KEY} -o "StrictHostKeyChecking=no" \
        root@anchor.${ROOT_DOMAIN} "systemctl restart ssh"
ssh -i ${SSH_KEY} root@anchor.${ROOT_DOMAIN} \
        "echo \"${SSH_PUB}\" >> /root/.ssh/authorized_keys && echo \"${SSH_PUB}\" >> ~/.ssh/authorized_keys"
ansible-playbook --key-file ${SSH_KEY} \
    -i ./hosts -e "ROOT_DOMAIN=${ROOT_DOMAIN} \
    HEADER_AUTH=${HEADER_AUTH} REG_CODE=${REG_CODE} DEBUG_DB=${DEBUG_DB} \
    ansible_python_interpreter=$(which python3)" \
    ./anchor.yml
