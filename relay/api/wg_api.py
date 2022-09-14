# Functions for managing multi-tenant Wireguard server
import wgconfig, os, logging, base64, ipaddress, json, np_db, os, subprocess, requests
from datetime import datetime, timedelta
from subprocess import Popen, PIPE

logging.root.setLevel(logging.INFO)
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

# Important note:
# Pubkey provided by controller is b64-encoded;
# We decode it before we hand it off to wgconfig and
# re-encode when we query the db so we can keep it URL-safe

interface = 'wg0'
root_domain = os.getenv('ROOT_DOMAIN')
wc = wgconfig.WGConfig('/etc/wireguard/wg0.conf')
subnet = ipaddress.ip_network('10.13.13.0/24')
hosturl = f'relay.{root_domain}'

# Generate the public key for the server's private key
def wg_pubkey():
    wc.read_file()
    privkey = wc.interface['PrivateKey']
    raw_pub = Popen(f'echo {privkey}|wg pubkey', stdout=PIPE, stderr=None, shell=True).communicate()[0]
    srv_pub = raw_pub.strip().decode('utf-8')
    return srv_pub

srv_pubkey = wg_pubkey()

# Reset interface
def restart_wg():
    hook_auth = os.getenv('HOOK_AUTH')
    url = f"http://172.20.0.2:9000/hooks/restart-wg?token={hook_auth}"
    resp = requests.get(url)
    if resp.status_code == 200:
        logging.info('[WG]: WG interface restarted')
        return True
    else:
        logging.warn(f'[WG]: Could not restart WG: {resp.status_code}')
        return False

# Does this pubkey exist?
def check_peer(pubkey):
    wc.read_file()
    pubkey = pubkey_decode(pubkey)
    peer_list = list(dict.keys(wc.peers))
    if pubkey in peer_list:
        # Return its IP if so
        peer_ip = wc.peers[pubkey]['AllowedIPs']
        peer_ip = str(ipaddress.ip_network(peer_ip)[0])
        return peer_ip
    else:
        return False

# Generate and return client configuration
def get_conf(pubkey):
    wc.read_file()
    pubkey = pubkey_decode(pubkey)
    peer_ip = wc.peers[pubkey]['AllowedIPs']
    port = wc.interface['ListenPort']
    template = f'''[Interface]
PrivateKey = privkey
Address = {peer_ip}
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = {srv_pubkey}
AllowedIPs = 0.0.0.0/0
Endpoint = {hosturl}:{port}
PersistentKeepalive = 20'''
    temputf = template.encode('utf-8')
    confb64 = base64.b64encode(temputf).decode('utf-8')
    return confb64

# Create a new peer with a label
def new_peer(label,pubkey):
    wc.read_file()
    avail_ip = next_ip(pubkey)
    logging.info(f'[WG]: Provisioning {avail_ip} for {pubkey}')
    if check_peer(pubkey) == False:
        try:
            dec_pubkey = pubkey_decode(pubkey)
            wc.add_peer(dec_pubkey)
            wc.add_attr(f'{dec_pubkey}','AllowedIPs',f'{avail_ip}')
            wc.write_file()
            restart_wg()
            conf = get_conf(pubkey)
            np_db.upd_value('anchors','conf',conf,'pubkey',pubkey)
            return True
        except Exception as e:
            logging.exception(f'[WG]: Provisioning error: {e}')
            return False
    else:
        return True

# Return a list of all peers (b64'd)
def peer_list():
    wc.read_file()
    peerlist = list(wc.peers)
    returnlist = []
    for peer in peerlist:
        # We have to add a \n so that it will match that generated
        # by `wg genkey|wg pubkey|base64 -w 0`
        peer = f'{peer}\n'
        peer = peer.encode('utf-8')
        peer = base64.b64encode(peer).decode('utf-8')
        returnlist.append(peer)
    return returnlist

# Delete a peer or list of peers
def del_peer(pubkey):
    if isinstance(pubkey,list):
        count = 0
        for peer in pubkey:
            if check_peer(peer) != False:
                try:
                    pub = pubkey_decode(peer)
                    wc.del_peer(pub)
                    wc.write_file()
                    count += 1
                    logging.info(f'[WG]: Peer {peer} deleted')
                except Exception as e:
                    logging.exception(f'[WG]: Peer {peer} not deleted:',e)
        restart_wg()
    elif isinstance(pubkey,str):
        if check_peer(pubkey) != False:
            try:
                pubkey = pubkey_decode(pubkey)
                wc.del_peer(pubkey)
                wc.write_file()
                logging.info(f'[WG]: Peer {pubkey} deleted')
                restart_wg()
                return
            except Exception as e:
                logging.exception(f'[WG]: Peer {pubkey} not deleted:',e)
                return e
    else:
        logging.warning(f'[WG] Invalid pubkey for deletion: {pubkey}')

# Convert b64 pubkey to wg format
def pubkey_decode(pubkey):
    pubkey = base64.b64decode(pubkey)
    return pubkey.strip().decode('utf-8')

# Returns a /32 IPv4Network type
def next_ip(pubkey):
    wc.read_file()
    pubkey = pubkey_decode(pubkey)
    peer_list = list(dict.keys(wc.peers))
    # If we already have this pubkey, return the IP
    if pubkey in peer_list:
        return ipaddress.ip_network(wc.peers[pubkey]['AllowedIPs'])
    else:
        ip_list, net_list = [], []
        for index in range(0,3):
            ip_list.append(subnet[index])
        for peer in peer_list:
            # Construct a list of used & reserved addresses
            net_list.append(ipaddress.ip_network(wc.peers[peer]['AllowedIPs']))
            for net in net_list:
                ip_list.append(net[0])
        # Dedupe and get the next available
        ip_list = list(dict.fromkeys(ip_list))
        hosts_iterator = (host for host in subnet.hosts() if host not in ip_list)
        avail_ip = next(hosts_iterator)
        return ipaddress.ip_network(f'{avail_ip}/32')
