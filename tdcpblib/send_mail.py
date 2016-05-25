#!/usr/bin/python
# -*- coding: utf-8 -*-
# -*- Mode: Python -*-
# vim:si:ai:et:sw=4:sts=4:ts=4

import smtplib
import time

from . import logger

def send_email_to(p_msg, p_receivers, p_smtp_server):

    for _receiver in p_receivers:
        if p_msg.has_key('To'):
            p_msg.replace_header('To',_receiver)
        else:
            p_msg['To'] = _receiver
        logger.debug("Sending mail to %s"%(p_msg['To']))
        smtpSendMail(p_msg, p_smtp_server)
        time.sleep(0.5)


def smtpSendMail(p_msg, p_smtp_server):
    try:
        conn = smtplib.SMTP(p_smtp_server)
    except smtplib.SMTPException:
        logger.error(u"Impossible to send mail: connexion failed - smptlib exception" )
        return
    except smtplib.socket.error:
        logger.error(u"Impossible to send mail: connexion  failed - socket error")
        return

    try:
        conn.set_debuglevel(False)
        #print p_msg.as_string()
        conn.sendmail(p_msg['From'], p_msg['To'], p_msg.as_string())
    except:
        logger.error(u"Impossible to send mail")
    finally:
        conn.close()


