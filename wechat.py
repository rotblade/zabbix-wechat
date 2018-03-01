#!/usr/local/anaconda3/envs/zabbix/bin/python
#_*_coding:utf-8 _*_
import os, sys, configparser, logging, urllib3, json
import requests


def setupLogger(name, logfile):
    formatter = logging.Formatter('{asctime} {name} {levelname} {message}',
                                  style='{')
    fh = logging.FileHandler(logfile)
    fh.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(fh)

    return logger


def getToken(url, params, proxy):
    r_token = requests.get(url=url, params=params, proxies=proxy)

    if r_token.json()['errcode']:
        raise Exception(r_token.json()['errmsg'])

    return r_token.json()['access_token']


def sendMessage(token, url, params, proxy):
    url_with_token = f'{url}?access_token={token}'
    r_send = requests.post(url=url_with_token,
                           data=json.dumps(params),
                           proxies=proxy)
    return r_send


urllib3.disable_warnings()
config = configparser.ConfigParser()
config.read('/etc/zabbix/wechat.conf')


if __name__ == '__main__':
    logger = setupLogger('wechat-alert', config['filepath']['log'])

    if len(sys.argv) < 4:
        logger.warn('Require 3 command arguments')
        sys.exit(1)

    sendto = sys.argv[1]
    subject = sys.argv[2]
    content = sys.argv[3]

    token_url = config['apiurl']['getToken']
    token_file = config['filepath']['token']
    token_params = {
        "corpid": config['id']['corpId'],
        "corpsecret": config['id']['appSecret'],
    }

    send_url = config['apiurl']['sendMessage']
    msg_params = {
        'toparty': sendto if sendto else config['id']['partyId'],
        'msgtype': 'text',
        'agentid': config['id']['appAgentId'],
        'text': {
            'content': subject + '\n' + content
        },
        'safe': '0'
    }

    proxy = {}
    for k in config['proxy']:
        proxy[k] = config['proxy'][k]

    token = ''
    if os.path.exists(token_file):
        with open(token_file, 'r') as f:
            token = f.read()
    else:
        try:
            token = getToken(token_url, token_params, proxy)
            with open(token_file, 'w') as f:
                f.write(token)
        except Exception as e:
            logger.error(e)
            sys.exit(1)

    try:
        r = sendMessage(token, send_url, msg_params, proxy)
    except Exception as e:
        logger.error(e)
        sys.exit(1)

    
    if r.json()['errcode']:
        if r.json()['errcode'] == 42001:
            try:
                token = getToken(token_url, token_params, proxy)
                r = sendMessage(token, send_url, msg_params, proxy)
                with open(token_file, 'w') as f:
                    f.write(token)
            except Exception as e:
                logger.error(e)
                sys.exit(1)
    
        else:
            logger.error(r.json()['errmsg'])
            sys.exit(1)

    logger.info('Sent to wechat successfuly!')
