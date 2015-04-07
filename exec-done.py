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
import string

import shutil

from smtplib import SMTP as SMTP       # this invokes the secure SMTP protocol (port 465, uses SSL)
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
import subprocess as SP
import json
from logging.handlers import SysLogHandler

logger = logging.getLogger('TdcpbLogger')
logger.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(levelname)s %(message)s # %(filename)s %(funcName)s l %(lineno)d')

syslog_handler = SysLogHandler(address="/dev/log")
syslog_handler.setFormatter(formatter)

logger.addHandler(syslog_handler)

logger.debug('This is a debug')

CONFIG_FILE="/etc/transmission-daemon/exec-done.json"

class TdcpbException(Exception):
    def __init__(self, message, errors = None):
        Exception.__init__(self, message)

class Lftp(object):
    LFTP_CMDS="set xfer:log true; mirror --verbose=3 -Rc {} {} ; quit"
    LFTP_SSL_CMDS="set ftp:ssl-force true; set ssl:verify-certificate no; set xfer:log true; mirror --verbose=3 -Rc {} {} ; quit"

    def __init__(self, p_dir_path, p_config_data) :
        self.config_data = p_config_data
        # TODO verfiy p_dir_path
        self.dir_path = p_dir_path
        if self.config_data['ftp-ssl']:
            lftp_tpl = self.LFTP_SSL_CMDS
        else:
            lftp_tpl = self.LFTP_CMDS
        if self.config_data['ftp-remote-path'] is None:
            logger.error('No remote path specified')
            sys.exit(1)
        if self.config_data['ftp-remote-path'] == "/":
            lftp_cmd = lftp_tpl.format( self.dir_path , '')
        else:
            if not (self.config_data['ftp-remote-path']).endswith("/"):
                logger.error("ftp-remote-path({}) shall ends with /, please verify".format(self.config_data['ftp-remote-path']))
                sys.exit(1)
            lftp_cmd = lftp_tpl.format( self.dir_path , self.config_data['ftp-remote-path'])
        _ftp_connect="ftp://{}:{}@{}".format(self.config_data['ftp-user'],
                                             self.config_data['ftp-pass'],
                                             self.config_data['ftp-host'])
        self.cmd = ["lftp",
            _ftp_connect,
            "-e",
            lftp_cmd
            ]
        logger.debug("Cmd: {}".format(" ".join(self.cmd)))


    def mirror(self):
        logger.info("Starting FTP copy of {}".format(os.path.basename(self.dir_path)))
        try :
            self.run_lftp()
        except TdcpbException as _err:
            logger.error("Copy of {} FAILED".format(os.path.basename(self.dir_path)))
            raise TdcpbException
        else:
            logger.info("Copy of {} successfull".format(os.path.basename(self.dir_path)))

    def run_lftp(self):
        sync = SP.Popen(self.cmd, stdout=SP.PIPE, stderr= SP.PIPE)
        (stdout, stderr) = sync.communicate()
        logger.debug( stdout)
        if sync.returncode:
            _msg = "FTP command failed"
            logger.error(_msg)
            logger.error(stderr)
            raise TdcpbException(_msg)


TPL_RECEPTION_OK = \
"""
Bonjour,

Vous avez reçu le DCP suivant:
DCP:                     $name
Date de Reception:       $time
Repertoire de reception: $dir
Machine:                 $hostname ($ip)

Cordialement
The DCP Bay
"""

TPL_RECEPTION_OK_FTP = \
"""
Bonjour,

Vous avez reçu le DCP suivant:
DCP:                     $name
Date de Reception:       $time
Repertoire de reception: $dir
Machine:                 $hostname ($ip)

RMQ: Le transfert du DCP vers la librairie est en cours.

Cordialement
The DCP Bay
"""

TPL_FTP_OK = \
"""
Bonjour
LE DCP $name à été transféré sur la librairie

Cordialement
The DCP Bay
"""

TPL_FTP_KO = \
"""
Bonjour
L transfert du DCP $name à échoué.

Vous pouvez nous joindre à contacter@tdcpb.org pour vous aider
à resoudre le problème

Cordialement
The DCP Bay
"""



def sendMailReceptionOk(p_torrent_msg, p_config_data) :
    _subject = "[INDE-CP] Reception de {} sur {}".format(p_torrent_msg["name"], p_torrent_msg["hostname"])
    if p_config_data['ftp-library']:
        _tpl = string.Template(TPL_RECEPTION_OK_FTP)
    else :
        _tpl = string.Template(TPL_RECEPTION_OK)

    _tpl_values = {
        'name'      : p_torrent_msg["name"],
        'time'      : p_torrent_msg["time"],
        'dir'       : p_torrent_msg["dir"],
        'hostname'  : p_torrent_msg["hostname"],
        'ip'        : p_torrent_msg["ip"],
        }

    _body = _tpl.substitute(_tpl_values)
    msg = MIMEMultipart()
    msg['Subject'] = _subject
    msg['From'] = p_config_data["expeditor"]

    msg['tdcpb-name'] = p_torrent_msg["name"]
    msg['tdcpb-reception'] = p_torrent_msg["time"]
    msg['tdcpb-reception-dir'] = p_torrent_msg["dir"]
    msg['tdcpb-hash'] = p_torrent_msg["hash"]
    msg['tdcpb-host'] = p_torrent_msg["hostname"]
    msg['tdcpb-ip'] = p_torrent_msg["ip"]
    msg.attach(MIMEText(_body, 'plain', "utf8"))
    for _receiver in p_config_data["receivers"]:
        if msg.has_key('To'):
            msg.replace_header('To',_receiver)
        else:
            msg['To'] = _receiver
        logger.info("Sending mail to %s"%(msg['To']))
        smtpSendMail(msg, p_config_data)
        time.sleep(0.5)

def sendMailFtpOk(p_torrent_msg, p_config_data) :
    _subject = "[INDE-CP] Transfert de {} sur la librairie finis".format(p_torrent_msg["name"])
    _tpl = string.Template(TPL_FTP_OK)
    _tpl_values = {
        'name'      : p_torrent_msg["name"],
        }
    _body = _tpl.substitute(_tpl_values)
    msg = MIMEMultipart()
    msg['Subject'] = _subject
    msg['From'] = p_config_data["expeditor"]

    msg['tdcpb-name'] = p_torrent_msg["name"]
    msg['tdcpb-reception'] = p_torrent_msg["time"]
    msg['tdcpb-reception-dir'] = p_torrent_msg["dir"]
    msg['tdcpb-hash'] = p_torrent_msg["hash"]
    msg['tdcpb-host'] = p_torrent_msg["hostname"]
    msg['tdcpb-ip'] = p_torrent_msg["ip"]
    msg['ftp-status'] = "OK"
    msg.attach(MIMEText(_body, 'plain', 'utf-8'))
    for _receiver in p_config_data["receivers"]:
        if msg.has_key('To'):
            msg.replace_header('To',_receiver)
        else:
            msg['To'] = _receiver
        logger.info("Sending mail to %s"%(msg['To']))
        smtpSendMail(msg, p_config_data)
        time.sleep(0.5)

def sendMailFtpKo(p_torrent_msg, p_config_data) :
    _subject = "[INDE-CP][ERREUR] Transfert de {} sur la librairie ".format(p_torrent_msg["name"])
    _tpl = string.Template(TPL_FTP_KO)
    _tpl_values = {
        'name'      : p_torrent_msg["name"],
        }
    _body = _tpl.substitute(_tpl_values)
    msg = MIMEMultipart()
    msg['Subject'] = _subject
    msg['From'] = p_config_data["expeditor"]

    msg['tdcpb-name'] = p_torrent_msg["name"]
    msg['tdcpb-reception'] = p_torrent_msg["time"]
    msg['tdcpb-reception-dir'] = p_torrent_msg["dir"]
    msg['tdcpb-hash'] = p_torrent_msg["hash"]
    msg['tdcpb-host'] = p_torrent_msg["hostname"]
    msg['tdcpb-ip'] = p_torrent_msg["ip"]
    msg['ftp-status'] = "KO"
    msg.attach(MIMEText(_body, 'plain', 'utf-8'))
    for _receiver in p_config_data["receivers"]:
        if msg.has_key('To'):
            msg.replace_header('To',_receiver)
        else:
            msg['To'] = _receiver
        logger.info("Sending mail to %s"%(msg['To']))
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
        logger.error(e)

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
    config_data = parseConfig(CONFIG_FILE)
    torrent_msg ={}
    torrent_msg["name"]     = os.environ.get('TR_TORRENT_NAME',  "ERROR_NO_NAME")
    torrent_msg["time"]     = os.environ.get('TR_TIME_LOCALTIME',"ERROR_NO_TIME")
    torrent_msg["dir"]      = os.environ.get('TR_TORRENT_DIR',   "ERROR_NO_DIR")
    torrent_msg["hash"]     = os.environ.get('TR_TORRENT_HASH',  "ERROR_NO_HASH")
    torrent_msg["id"]       = os.environ.get('TR_TORRENT_ID',    "ERROR_NO_ID")
    torrent_msg["ip"]       = get_tinc_ip()
    torrent_msg["hostname"] = get_hostname()
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
    sendMailReceptionOk(torrent_msg, config_data)
    if config_data['ftp-library'] :
        print "FTP vers la librairie"
        _dir_path = os.path.join(torrent_msg["dir"],torrent_msg["name"])
        ftp = Lftp(_dir_path, config_data)
        try:
            ftp.mirror()
        except:
            #smoething goes wrong in copy
            logger.error("FTP transfer FAIL")
            sendMailFtpKo(torrent_msg, config_data)
        else:
            # send mail copy to library ok
            sendMailFtpOk(torrent_msg, config_data)
            logger.info("FTP transfer OK")

if __name__ == "__main__":
   sys.exit(main(sys.argv))


