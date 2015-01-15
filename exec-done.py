#!/usr/bin/python
# -*- coding: utf-8 -*-
# -*- Mode: Python -*-
# vim:si:ai:et:sw=4:sts=4:ts=4


import time
import os
import argparse
import logging
import sys
import commands
import socket

import shutil

from smtplib import SMTP as SMTP       # this invokes the secure SMTP protocol (port 465, uses SSL)
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
import json

def sendMail(p_torrent_msg, p_config_data) :
    _subject = "Reception de {} sur {}".format(p_torrent_msg["name"], p_torrent_msg["hostname"])
    _body =  ""
    _str = "Bonjour\n"
    _body += _str
    _str = "Vous avez recu le DCP suivant:\n"
    _body += _str
    _str = "DCP               : {}\n".format(p_torrent_msg["name"])
    _body += _str
    _str = "Date de Reception : {}\n".format(p_torrent_msg["time"])
    _body += _str
    _str = "DCP repertoire    : {}\n".format(p_torrent_msg["dir"])
    _body += _str
    _str = "Torrent hash      : {}\n".format(p_torrent_msg["hash"])
    _body += _str
    _str = "Machine           : {}({})\n".format(p_torrent_msg["hostname"],p_torrent_msg["ip"])
    _body += _str

    _str = "\n"
    _body += _str
    _str = "Cordialement\n"
    _body += _str
    _str = "The DCP Bay\n"
    _body += _str

    msg = MIMEMultipart()
    msg['Subject'] = _subject
    msg['From'] = p_config_data["expeditor"]

    msg['tdcpb-name'] = p_torrent_msg["name"]
    msg['tdcpb-reception'] = p_torrent_msg["time"]
    msg['tdcpb-reception-dir'] = p_torrent_msg["dir"]
    msg['tdcpb-hash'] = p_torrent_msg["hash"]
    msg['tdcpb-host'] = p_torrent_msg["hostname"]
    msg['tdcpb-ip'] = p_torrent_msg["ip"]
    msg.attach(MIMEText(_body, 'plain'))
    for _receiver in p_config_data["receivers"]:
        if msg.has_key('To'):
            msg.replace_header('To',_receiver)
        else:
            msg['To'] = _receiver
        logging.info("Sending mail to %s"%(msg['To']))
        smtpSendMail(msg, p_config_data)
        time.sleep(0.5)

def smtpSendMail(p_msg, p_config_data):

    conn = SMTP(p_config_data["smtp"])
    conn.set_debuglevel(False)
    #conn.login(USERNAME, PASSWORD)
    try:
        #print p_msg.as_string()
        conn.sendmail(p_msg['From'], p_msg['To'], p_msg.as_string())
    finally:
        conn.close()

def WriteFile(p_path, p_contents):
    try:
        f = open(p_path, "w")
        try:
            f.writelines(p_contents) # Write a sequence of strings to a file
        finally:
            f.close()
    except IOError, e:
        logging.error(e)

def get_tinc_ip():
    _ips = commands.getoutput("hostname -I").split()
    for _ip in _ips:
        if _ip.startswith("10.10.10") :
            return _ip
    return None

def get_hostname():
    return socket.gethostname()

def parseConfig(p_config_file):
    json_data=open(p_config_file)
    data = json.load(json_data)
    json_data.close()
    return data

def main(argv):
    config_data = parseConfig("./exec-done.json")
    logging.basicConfig(format = '%(asctime)s %(levelname)s %(message)s # %(filename)s %(funcName)s l %(lineno)d', level=logging.ERROR)

    torrent_msg ={}
    torrent_msg["name"] = os.environ.get('TR_TORRENT_NAME',  "ERROR_NO_NAME")
    torrent_msg["time"] = os.environ.get('TR_TIME_LOCALTIME',"ERROR_NO_TIME")
    torrent_msg["dir"]  = os.environ.get('TR_TORRENT_DIR',   "ERROR_NO_DIR")
    torrent_msg["hash"] = os.environ.get('TR_TORRENT_HASH',  "ERROR_NO_HASH")
    torrent_msg["id"]   = os.environ.get('TR_TORRENT_ID',    "ERROR_NO_ID")
    torrent_msg["ip"]   = get_tinc_ip()
    torrent_msg["hostname"]   = get_hostname()
    mycontent = []
    mycontent.append("DCP               : {}\n".format(torrent_msg["name"]) )
    mycontent.append("Date de Reception : {}\n".format(torrent_msg["time"]) )
    mycontent.append("DCP repertoire    : {}\n".format(torrent_msg["dir"])  )
    mycontent.append("DCP hash          : {}\n".format(torrent_msg["hash"]) )
    mycontent.append("DCP id            : {}\n".format(torrent_msg["id"])   )
    mycontent.append("Machine IP        : {}\n".format(torrent_msg["ip"])   )
    mycontent.append("Hostname          : {}\n".format(torrent_msg["hostname"])   )

    #mycontent.append("Date de Generation: %s\n"%(time.strftime("%c")))
    WriteFile("/tmp/tdcpb-{}.log".format(torrent_msg["name"]), mycontent)
    sendMail(torrent_msg, config_data)


if __name__ == "__main__":
   sys.exit(main(sys.argv))


