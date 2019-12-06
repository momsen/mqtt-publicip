import argparse, re, time, subprocess, os, sys, traceback, json
import paho.mqtt.publish as publish
from configparser import SafeConfigParser

def get_public_ip(shell_cmd):
    proc = subprocess.Popen(shell_cmd, shell=True, stdout=subprocess.PIPE)
    try:
        outs, errs = proc.communicate(timeout=300)
    except subprocess.TimeoutExpired:
        proc.kill()
        outs, errs = proc.communicate()
    return outs.decode('UTF-8').strip()

def create_discovery_message(name, state_topic):
    return json.dumps({'name': name, 'state_topic': state_topic})

def publish_messages(ipv4, ipv6, cfg):
    auth = {'username': cfg['mqtt']['user'], 'password': cfg['mqtt']['pw']}
    discovery_msgs = [(cfg['ipv4']['discovery_topic'], create_discovery_message(cfg['ipv4']['discovery_name'], cfg['ipv4']['state_topic']), 0, True),\
                     (cfg['ipv6']['discovery_topic'], create_discovery_message(cfg['ipv6']['discovery_name'], cfg['ipv6']['state_topic']), 0, True)]
    try:
        publish.multiple(discovery_msgs, hostname=cfg['mqtt']['host'], client_id=cfg['mqtt']['client_id'], port=cfg['mqtt']['port'], auth=auth)
    except ConnectionError:
        print("Unable to publish discovery messages via mqtt:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

    state_msgs = [(cfg['ipv4']['state_topic'], ipv4, 0, False),\
                  (cfg['ipv6']['state_topic'], ipv6, 0, False)]
    try:
        publish.multiple(state_msgs, hostname=cfg['mqtt']['host'], client_id=cfg['mqtt']['client_id'], port=cfg['mqtt']['port'], auth=auth)
    except ConnectionError:
        print("Unable to publish state messages via mqtt:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

def read_config(filename):
    parser = SafeConfigParser()
    found = parser.read(filename)
    if not filename in found:
        print("The ini file " + filename + " was not found.", file=sys.stderr)
        sys.exit(-1)

    cfg = {}
    for section_definition in [ { 'name': 'mqtt', 'parameters': [ 'host', 'port', 'client_id', 'user', 'pw'] },\
                                { 'name': 'ipv4', 'parameters': ['discovery_topic', 'discovery_name', 'state_topic', 'shell']},\
                                { 'name': 'ipv6', 'parameters': ['discovery_topic', 'discovery_name', 'state_topic', 'shell']}]:

        section_name = section_definition['name']

        section = {}
        for parameter in section_definition['parameters']:
            if not parser.has_option(section_name, parameter):
                print("Parameter '" + parameter + "' is missing in section '" + section_name + "'", file=sys.stderr)
                sys.exit(-1)
            section[parameter] = parser.get(section_name, parameter)

        cfg[section_name] = section

    try:
        cfg['mqtt']['port'] = int(cfg['mqtt']['port'])
    except ValueError:
        print("The port " + cfg['mqtt']['port'] + " cannot be parsed as integer.", file=sys.stderr)
        sys.exit(-1)

    return cfg

parser = argparse.ArgumentParser(description="Run shell command to determin the public ip address by contacting a public DNS server and push the results via mqtt.")
parser.add_argument("inifile", type=str, action="store", help="name of the ini file")
args = parser.parse_args()

cfg = read_config(args.inifile)
publicIPV4 = get_public_ip(cfg['ipv4']['shell'])
publicIPV6 = get_public_ip(cfg['ipv6']['shell'])
publish_messages(publicIPV4, publicIPV6, cfg)

print('{};{};{};{}'.format(time.strftime('%y/%m/%d'), time.strftime('%H:%M'), publicIPV4, publicIPV6))
