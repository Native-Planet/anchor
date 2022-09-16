#!/bin/bash
######
# Don't edit below
######
source ./settings.sh
HEADER_AUTH=$(echo $RANDOM | md5sum | head -c 20)
if command -v apt &> /dev/null
then
    sudo apt update && sudo apt install -y python3 ansible
elif ! command -v apt &> /dev/null
then
    if ! command -v python3 &> /dev/null
        then
        echo "Please install Python 3"
        exit
    elif ! command -v ansible-playbook &> /dev/null
        then
        echo "Please install Ansible"
        exit
    fi
fi
chmod 600 ${SSH_KEY}
mkdir -p /home/ubuntu/.ssh
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
    HEADER_AUTH=${HEADER_AUTH} REG_CODE=${REG_CODE} DEBUG_DB=${DEBUG_DB} \
    ansible_python_interpreter=$(which python3)" \
    ./relay.yml
