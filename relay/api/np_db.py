from datetime import datetime, timedelta
from flask import request
from time import sleep
import sqlite3, os, json, base64, logging, requests, socket, caddy_api, wg_api, sg_api
from requests import get


logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
header_auth = os.getenv('HEADER_AUTH')
root_domain = os.getenv('ROOT_DOMAIN')
db_path = os.getenv('DB_PATH')
db = sqlite3.connect(db_path, isolation_level=None)

# █▀ █▀█ █░░ █ ▀█▀ █▀▀ 
# ▄█ ▀▀█ █▄▄ █ ░█░ ██▄ 
# Functions for remote DB operations

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# Create DB record for new client
# Update lease on existing
def add_reg(reg_code):
    sub_id = hash(reg_code)
    exists = get_value('anchors','uid','sub_id',sub_id)
    if exists == None:
        timestamp = datetime.now()
        conn = sqlite3.connect(db_path, isolation_level=None)
        conn.execute('pragma journal_mode=wal;')
        query = f'INSERT INTO anchors (sub_id, created, last_mod) \
                VALUES ("{sub_id}", "{timestamp}", \
                "{timestamp}");'
        cur = conn.cursor()
        cur.execute(query)
        conn.commit()
        logging.info(f"• [DB:anchors] CREATE slot {sub_id} @ {timestamp}")
    else:
        upd_value('anchors','lease',lease,'uid',exists)
# Lookup value for an index and key
# ex: from `anchors` get `@p` for `pubkey` = `<whatever>`
def get_value(db,lookup,key,value):
    query = f'SELECT {lookup} FROM {db} WHERE {key} is "{value}" LIMIT 1;'
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.execute('pragma journal_mode=wal;')
    conn.row_factory = dict_factory
    cur = conn.cursor()
    answer_raw = cur.execute(query).fetchall()
    if not answer_raw:
        return None
    else:
        answer_json = json.loads(json.dumps(answer_raw))
        result = answer_json[0][lookup]
        return result

# Return a list of items
def get_values(db,lookup,key,value):
    query = f'SELECT {lookup} FROM {db} WHERE {key} is "{value}";'
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.execute('pragma journal_mode=wal;')
    cur = conn.cursor()
    answer_raw = cur.execute(query).fetchall()
    if not answer_raw:
        return None
    else:
        output_list = []
        for item_lists in answer_raw:
            for item in item_lists:
                output_list.append(item)
        return output_list

# Get service for specific client
def get_client_value(db,lookup,key,value,pubkey):
    query = f'SELECT {lookup} FROM {db} WHERE {key} is "{value}" AND pubkey is "{pubkey}";'
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.execute('pragma journal_mode=wal;')
    conn.row_factory = dict_factory
    cur = conn.cursor()
    answer_raw = cur.execute(query).fetchall()
    if not answer_raw:
        return None
    else:
        output_list = []
        for item_lists in answer_raw:
            for item in item_lists:
                output_list.append(item)
        return output_list

# Return entire row
def get_row(db,key,value):
    query = f'SELECT * FROM {db} WHERE {key} is "{value}";'
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.execute('pragma journal_mode=wal;')
    conn.row_factory = dict_factory
    cur = conn.cursor()
    answer_raw = cur.execute(query).fetchall()
    if not answer_raw:
        return None
    else:
        return answer_raw

# Create DB record for new service
def create_svc(pubkey,subdomain,svc_type):
    timestamp = datetime.now()
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.execute('pragma journal_mode=wal;')
    query = f'INSERT INTO services (pubkey, subdomain, svc_type, \
            status, created, last_mod) VALUES ("{pubkey}", "{subdomain}", \
            "{svc_type}", "creating", "{timestamp}", "{timestamp}");'
    cur = conn.cursor()
    cur.execute(query)
    conn.commit()
    logging.info(f"• [DB:services] CREATE {svc_type} {subdomain} @ {timestamp}")

def get_client_svcs(pubkey):
    logging.info(f'[DB:services]: GET client services {pubkey}')
    url = 'http://localhost:8090/v1/retrieve'
    headers = {"Content-Type": "application/json"}
    clients_url = f"{url}?pubkey={pubkey}"
    try:
        response = requests.get(clients_url, headers=headers).json()
        return response
    except Exception as e:
        logging.exception(e)
        return []


# █▀▄ █▄░█ █▀
# █▄▀ █░▀█ ▄█

def check_dns(url):
    try:
        my_ip = get('https://api.ipify.org').content.decode('utf8')
        subdomain_ip = socket.gethostbyname(url)
        if subdomain_ip != my_ip:
            return False
        else:
            return True
    except Exception as e:
        logging.exception(f'[DNS]: Could not resolve DNS: {url}')
        return False


# █▀ █░█ █▀▀
# ▄█ ▀▄▀ █▄▄
def rectify_svc_list(pubkey):
    '''
    get pubkey
    add URL/upstream to a dictionary
    make sure DNS records are correct
    check Caddy upstream for each URL in dict
    delete any routes that aren't in dict
    '''
    no_proxy = ['urbit-ames','minio-console']
    caddy_conf = caddy_api.get_conf()['apps']['http']['servers']['srv0']['routes']
    svc_list, caddy_list = [hostname], []
    services, minios = {}, {}
    peerlist = wg_api.peer_list()
    del_peers = []
    for pubkey in clients:
        svcs = get_client_svcs(pubkey)
        peer_ip = wg_api.check_peer(pubkey)
        # Make sure we have the pubkey registered
        if peer_ip == False:
            wg_api.new_peer(pubkey=pubkey,label=None)
            peer_ip = wg_api.check_peer(pubkey)
        if svcs['subdomains'] != []:
            for svc in svcs['subdomains']:
                # Build a list of subdomains
                url = svc['url']
                svc_type = svc['svc_type']
                port = svc['port']
                # Add missing DNS entries
                if 'ames.' not in url:
                    dns_check = check_dns(f'url.{root_domain}')
                    if dns_check = False:
                        logging.warning('A record does not match public IP!')
                subd = url.removesuffix(f'.{root_domain}')
                # Append to dictionary of all services
                # We don't want a reverse proxy for ames
                if hostname not in services:
                    services[hostname] = 'api:8090'
                if (svc_type not in no_proxy) and (port != None):
                    services[subd]=f'{peer_ip}:{port}'
                if (svc_type == 'minio-console') and (port != None):
                    minios[subd]=f'{peer_ip}:{port}'

        # Create a list of current Caddy routes
        for route in caddy_conf:
            subd = route['@id']
            caddy_list.append(subd)

        # Delete any routes that aren't on the DB list
        for route in caddy_list:
            if (route not in services) and (route not in minios):
                caddy_api.remove_url(route)

        # Validate upstream for each service
        for subd in services:
            upstr = services[subd]
            if caddy_api.check_upstream(subd,upstr) == False:
                caddy_api.add_reverse_proxy(subd, host=f'{root_domain}',upstream=upstr)
                sleep(3)

        # Validate upstream for minios
        for subd in minios:
            upstr = minios[subd]
            if caddy_api.check_upstream(subd,upstr) == False:
                caddy_api.add_minio(subd, host=f'{root_domain}',upstream=upstr)
                sleep(3)

        # Delete pubkeys that aren't on client list
        for peer in peerlist:
            if peer not in clients:
                del_peers.append(peer)
        if del_peers != []:
            wg_api.del_peer(del_peers)

    for pubkey in clients:
        upd_value('services','status','ok','pubkey',pubkey)

def valid_wg(pubkey):
    try:
        pub_raw = ((base64.b64decode(pubkey).strip().decode("utf-8")))
        if(int(len(pub_raw.strip('='))*(3/4)) == 32):
            return True
        else:
            raise Exception('invalid pubkey (needs to be 32 byte value)')
            return False
    except Exception as e:
        logging.warning("• Invalid pubkey (needs to be utf-8 base64 string)")
        logging.exception(e)
        return False

# Determine random unused port for service
def port_gen(svc_type,instanceid):
    port_records = get_values('services','port','instanceid',instanceid)
    if port_records == None:
        port_records = []
    else:
        if svc_type == 'urbit-web':
            port = random.randrange(80,9999)
            while port in port_records:
                port = random.randrange(80,9999)
            return port
        if svc_type == 'urbit-ames':
            port = random.randrange(30000,40000)
            while port in port_records:
                port = random.randrange(30000,40000)
            return port
        if svc_type in ['minio','minio-console','minio-bucket']:
            port = random.randrange(10000,15000)
            while port in port_records:
                port = random.randrange(10000,15000)
            return port
        else:
            return None

# Make sure input is a valid subdomain
def subdomain_validate(domain):
    result = re.match('''
        (?=^.{,253}$)          # max. length 253 chars
        (?!^.+\.\d+$)          # TLD is not fully numerical
        (?=^[^-.].+[^-.]$)     # doesn't start/end with '-' or '.'
        (?!^.+(\.-|-\.).+$)    # levels don't start/end with '-'
        (?:[a-z\d-]            # uses only allowed chars
        {1,63}(\.|$))          # max. level length 63 chars
        {1,12}                 # max. 12 levels
        ''', domain, re.X | re.I)
    if result == None:
        return False
    else:
        return True

# Supported service types
def svc_validate(svc_type):
    svc_list = [ 'urbit', 'minio' ]
    if svc_type not in svc_list:
        return False
    else:
        return True

# Validate requests to /create
def validate_inputs(subdomain,pubkey,svc_type):
    is_valid = []
    if valid_wg(pubkey) == False:
        is_valid.append('Invalid pubkey')    
    if subdomain_validate(subdomain) == False:
        is_valid.append('Invalid subdomain')
    if svc_validate(svc_type) == False:
        is_valid.append('Unsupported service')
    if is_valid != []:
        return is_valid
    else:
        return True