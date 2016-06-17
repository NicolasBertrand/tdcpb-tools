#!/usr/bin/python
# -*- coding: utf-8 -*-
# -*- Mode: Python -*-
# vim:si:ai:et:sw=4:sts=4:ts=4

import os
import logging
import sys
import json
import socket
from time import sleep
from datetime import datetime
from datetime import timedelta

from transmissionrpc import HTTPHandlerError, TransmissionError
from transmissionrpc import Client as TClient


from common import TdcpbException
from . import logger

TRANSMISSION_CLIENT = "transmission"
DELUGE_CLIENT       = "deluge"

CLIENT_TYPE = [
        TRANSMISSION_CLIENT,
        DELUGE_CLIENT]

class BTCexception(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class BitTorrentClient(object):
    def __init__(self,client_type = TRANSMISSION_CLIENT):
        self.client_type= client_type
    def connect(self, address, port, user, password):
        pass
    def get_torrents(self):
        pass
    def add_torrent(self, torrent_path):
        pass
    def remove(self, torrent_name):
        pass

class TransmissionClient(BitTorrentClient):
    DELETE_TIMEOUT = 240

    def __init__(self):
        BitTorrentClient.__init__(self, TRANSMISSION_CLIENT)
        self.dict_client={}

    def connect(self, address, port, user, password):
        try :
           self.client =TClient( address, port, user, password)
        except TransmissionError as err:
            raise TdcpbException(" {} TransmissionError {}".format(address, err))
        except socket.timeout as err:
            raise TdcpbException( " {} Socket error {}".format( address,  err))
        else:
            self.dict_client['name']= address

    def get_torrents(self):
        tr_torrents = self.client.get_torrents()
        self.dict_client['torrents']= []
        for _torrent in tr_torrents:
            _torrent_dict = {
            u'name'         : _torrent.name,
            u'hash'         : _torrent.hashString,
            u'progress'     : _torrent.progress,
            u'status'       : _torrent.status,
            u'date_active'  : _torrent.date_active,
            u'date_added'   : _torrent.date_added,
            u'date_started' : _torrent.date_started,
            u'date_done'    : _torrent.date_done,
            u'eta'          : -1,
            u'error'        : _torrent.error,
            u'errorString'  : _torrent.errorString[:350],
            }
            #TODO: Warning eta can return exception ValuerError

            try:
               _torrent_dict[ u'eta']          = timedelta.total_seconds(_torrent.eta)
            except ValueError:
                pass
            self.dict_client['torrents'].append(_torrent_dict)
            if _torrent_dict[u'error'] == 3:
                _torrent_dict[u'status'] = u'error_torrentclient'
            if _torrent_dict[u'error'] in [1,2]:
                _torrent_dict[u'status'] = u'error_torrenttracker'

        return self.dict_client
    def add_torrent(self, torrent_path):
        pass
    def remove(self, torrent_hash, delete_data = False) :
        if delete_data:
            # increase temeout wgne deleting data
            self.client.remove_torrent(torrent_hash,
                                     delete_data = delete_data,
                                     timeout = self.DELETE_TIMEOUT )
        else:
            self.client.remove_torrent(torrent_hash)

    def verify(self, torrent_hash):
        self.client.verify_torrent(torrent_hash)


def main(argv):
    pass
