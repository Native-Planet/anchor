# ███╗░░██╗██████╗░  ░█████╗░██████╗░██╗
# ████╗░██║██╔══██╗  ██╔══██╗██╔══██╗██║
# ██╔██╗██║██████╔╝  ███████║██████╔╝██║
# ██║╚████║██╔═══╝░  ██╔══██║██╔═══╝░██║
# ██║░╚███║██║░░░░░  ██║░░██║██║░░░░░██║
# ╚═╝░░╚══╝╚═╝░░░░░  ╚═╝░░╚═╝╚═╝░░░░░╚═╝ 
# NativePlanet API server / ~sitful-hatred
from flask import Flask, request, jsonify, redirect
from datetime import datetime, timedelta
from gevent.pywsgi import WSGIServer
from time import sleep
import sqlite3, os, socket, json, threading, logging, ipaddress, base64, re
import wg_api, caddy_api, np_db

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

root_domain = os.getenv('ROOT_DOMAIN')
reg_code = os.getenv('REG_CODE')
debug_db = os.getenv('DEBUG_DB')

np_db.db.execute('CREATE TABLE IF NOT EXISTS anchors (uid INTEGER, \
            reg_id TEXT NULL, pubkey TEXT NULL, conf TEXT NULL, \
            status TEXT NULL, created TIMESTAMP NULL, \
            last_mod TIMESTAMP NULL, PRIMARY KEY ("uid" AUTOINCREMENT) );')
np_db.db.execute('CREATE TABLE IF NOT EXISTS services (uid INTEGER, \
            pubkey TEXT NULL, port INTEGER NULL, subdomain TEXT NULL, \
            svc_type TEXT NULL, status TEXT NULL, created TIMESTAMP NULL, \
            last_mod TIMESTAMP NULL, PRIMARY KEY ("uid" AUTOINCREMENT) );')

dns_check = np_db.check_dns(f'relay.{root_domain}')
if dns_check == False:
    print('Please configure DNS (see readme)')
    raise SystemExit
if reg_code != None:
    reg_id = hash(reg_code)
    np_db.add_reg(reg_id)
else:
    print('Please provide a registration code (see readme)')
    raise SystemExit

# Register subdomain for node API
if caddy_api.check_upstream(f'relay.{root_domain}','api:8090') != True:
    caddy_api.add_reverse_proxy('relay', host=f'{root_domain}', upstream='api:8090')
    sleep(3)
    caddy_api.add_502()
    if debug_db == 'true':
        caddy_api.add_reverse_proxy('db', host=f'{root_domain}', upstream='dbweb:8080')

app = Flask(__name__)

# Root path -- redirect to public site
@app.route('/', methods=['GET'])
def home():
    return redirect(f"https://nativeplanet.io", code=302)

# Route to register a new client
@app.route('/v1/register', methods=['POST'])
def register_client():

    timestamp = datetime.now()
    headers = request.headers
    fwd_ip = headers.get("X-Forwarded-For")
    content = request.get_json()
    reg_code = content.get('reg_code')
    pubkey = content.get('pubkey')
    code_hash = hash(reg_code)

    logging.info(f"\n\n===\n {timestamp} \n• {code_hash} {fwd_ip} REGISTER\n---\n{pubkey}\n---")

    result = np_db.reg_client(pubkey,reg_code)

    return jsonify(
        action = 'register',
        debug = result['debug'],
        error = result['error'],
        pubkey = pubkey,
        lease = np_db.lease
    ),result['reqstatus']


# Route to request record for an existing anchor
@app.route('/v1/retrieve', methods=['GET'])
def retrieve_info():

    timestamp = datetime.now()
    headers = request.headers
    fwd_ip = headers.get("X-Forwarded-For")
    pubkey = request.args.get('pubkey')
    exists = np_db.get_value('anchors','uid','pubkey',pubkey)
    return_error = None
    debug = None
    conf = None
    debug = 'Pubkey is not registered'
    error = 1
    status = 'No record'
    reqstatus = 400
    subdomains = []

    logging.info(f"\n\n===\n{timestamp} • {fwd_ip} INFO\n/v1/retrieve?pubkey={pubkey}\n---")

    if exists != None:
        anchor = np_db.get_row('anchors','pubkey',pubkey)[0]
        conf = anchor['conf']
        status = anchor['status']
        debug = None
        error = 0
        reqstatus = 200
        svc_list = np_db.get_values('services','uid','pubkey',pubkey)
        if svc_list != None:
            for svc in svc_list:
                row = np_db.get_row('services','uid',svc)[0]
                for i, name in enumerate(row):
                    if row[name] is None:
                        row[name] = 'null'
                subd = row['subdomain']
                svc_object = {'url': f'{subd}.{root_domain}',
                'status': row['status'],
                'svc_type': row['svc_type'],
                'port': row['port']}
                subdomains.append(svc_object)
        else:
            subdomains = []

    response = {'action':'retrieve',
    'conf':conf,
    'debug':debug,
    'error':error,
    'pubkey':pubkey,
    'status':status,
    'subdomains':subdomains,
    'lease': np_db.lease}
    return jsonify(response),reqstatus

# Route to create anchor instance record
@app.route('/v1/create', methods=['POST'])
def add_anchor():
    
    headers = request.headers
    content = request.get_json()
    fwd_ip = headers.get("X-Forwarded-For")
    subdomain = content.get('subdomain').lower()
    pubkey = content.get('pubkey')
    svc_type = content.get('svc_type')
    return_error = None
    timestamp = datetime.now()

    logging.info(f"\n\n===\n{timestamp}\n•{subdomain} {fwd_ip} CREATE\n---\n{content}\n---")

    validation = np_db.validate_inputs(subdomain,pubkey,svc_type)
    if validation == True:
        svc_exists = np_db.get_value('services','pubkey','subdomain',subdomain)
        if svc_exists == None:
            response = np_db.new_pass(subdomain,pubkey,svc_type)
            threading.Thread(target=np_db.rectify_svc_list, name='rectify', args=(pubkey,)).start()
            return jsonify(response)
        elif svc_exists != pubkey:
            np_db.upd_value('services','pubkey',pubkey,'pubkey',svc_exists)
            threading.Thread(target=np_db.rectify_svc_list, name='rectify', args=(pubkey,)).start()
            response = np_db.return_existing(subdomain,pubkey,svc_type)
            return jsonify(response)
        else:
            response = np_db.return_existing(subdomain,pubkey,svc_type)
            return jsonify(response)
    else:
        response = np_db.invalid_fail(subdomain,pubkey,svc_type,validation)
        return jsonify(response)


if __name__ == "__main__":
    http_server = WSGIServer(('0.0.0.0', 8090), app)
    http_server.serve_forever()