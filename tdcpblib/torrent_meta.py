#!/usr/bin/python
# -*- coding: utf-8 -*-
# -*- Mode: Python -*-
# vim:si:ai:et:sw=4:sts=4:ts=4

import os.path
from datetime import datetime

import bencode
import hashlib

from common import TdcpbException
from . import logger

class TorrentMeta(object):

    def __init__(self, p_torrent_path):
        if not os.path.exists(p_torrent_path):
            _err =  "torrent path not exist: {}".format(p_torrent_path)
            raise TdcpbException(_err)

    @classmethod
    def info(cls, p_torrent_path):
        if not os.path.exists(p_torrent_path):
            _err =  "torrent path not exist: {}".format(p_torrent_path)
            raise TdcpbException(_err)
        _torrent_info = {}
        (_info, _metainfo) = cls._get_torrent_meta(p_torrent_path)
        _torrent_info['name'] = _info['name']
        _torrent_info['hash'] = cls._calc_hash(_info)
        _torrent_info['creation_date'] = datetime.fromtimestamp(_metainfo['creation date'])
        _size = 0
        for _f in _info['files']:
            _size = _size + int(_f['length'])
        _torrent_info['size'] = _size
        return _torrent_info

    @staticmethod
    def _get_torrent_meta(p_torrent_path):
        _torrent_file = open(p_torrent_path, "rb")
        _metainfo = bencode.bdecode(_torrent_file.read())
        _info = _metainfo['info']
        _torrent_file.close()
        return (_info, _metainfo)

    @staticmethod
    def _calc_hash (p_info):
        return  hashlib.sha1(bencode.bencode(p_info)).hexdigest()

