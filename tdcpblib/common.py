#!/usr/bin/python
# -*- coding: utf-8 -*-
# -*- Mode: Python -*-
# vim:si:ai:et:sw=4:sts=4:ts=4

import json

import logging
from logging.handlers import TimedRotatingFileHandler

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

