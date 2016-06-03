#!/usr/bin/python
# -*- coding: utf-8 -*-
# -*- Mode: Python -*-
# vim:si:ai:et:sw=4:sts=4:ts=4

import json
import socket
import logging
import commands
from logging.handlers import TimedRotatingFileHandler
import netrc

class TdcpbException(Exception):
    def __init__(self, message, errors = None):
        Exception.__init__(self, message)

def parseConfig(p_config_file):
    json_data=open(p_config_file)
    data = json.load(json_data)
    json_data.close()
    return data

def create_logger():
    logger = logging.getLogger('TdcpbLogger')
    logger.setLevel(logging.INFO)

    # create formatter
    formatter = logging.Formatter('%(levelname)s %(asctime)s %(message)s # %(filename)s %(funcName)s l %(lineno)d')

    try :
        file_handler = TimedRotatingFileHandler('/var/log/tdcpb/tdcpb.log', when='D')
    except IOError:
        pass
    else:
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    ch.setLevel(logging.INFO)

    logger.addHandler(ch)

    return logger

def get_tinc_ip():
    _ips = commands.getoutput("hostname -I").split()
    for _ip in _ips:
        if _ip.startswith("10.10.10") :
            return _ip
    return None

def get_hostname():
    return socket.gethostname()


def get_host_torrent_login(p_hostname):
    _netrc = netrc.netrc()
    if p_hostname not in _netrc.hosts:
        _err = u'Host {} unknown'.format(p_hostname)
        raise TdcpbException(_err)
    return _netrc.authenticators(p_hostname)


def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)
