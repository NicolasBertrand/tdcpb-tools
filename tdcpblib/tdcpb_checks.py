#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Mode: Python -*-
# vim:si:ai:et:sw=4:sts=4:ts=4
#
import os.path


from common import TdcpbException
from . import logger
import di_parser as T_PARSER

def tdcpb_check_short(p_dcp_folder):
    _dcp_folder = os.path.abspath(p_dcp_folder)
    logger.info('File check started for {}'\
        .format(os.path.basename(_dcp_folder)))
    # do some basic check
    if not os.path.exists(_dcp_folder):
        _msg = "dcp directory {} does not exist"\
            .format(_dcp_folder)
        raise TdcpbException(_msg)
    #TODO : why not use normpath ?
    try :
        DCP = T_PARSER.DiParser(_dcp_folder)
        _nb = DCP.check_files()
    except T_PARSER. DiError as _err:
        raise TdcpbException(_err)
    if _nb == 0:
        _err = "DCP {} not well formed "\
            .format(os.path.basename(_dcp_folder))
        raise TdcpbException(_err)
    logger.info('File check OK for {}'\
        .format(os.path.basename(_dcp_folder)))

def tdcpb_check_long(p_dcp_folder):
    logger.info("Hash Check started for {}"\
        .format(os.path.basename(p_dcp_folder)))
    # do some basic check
    if not os.path.exists(p_dcp_folder):
        _msg = "dcp directory {} does not exist"\
            .format(p_dcp_folder)
        raise TdcpbException(_msg)

    _dcp_folder = os.path.abspath(p_dcp_folder)
    try :
        DCP = T_PARSER.DiParser(_dcp_folder)
        _res = DCP.check_hash()
    except T_PARSER. DiError as _err:
        raise TdcpbException(_err)
    if _res is not 'OK':
        _err = "DCP hash verfication failed"
        raise TdcpbException(_err)
    logger.info("Hash OK for {}". \
            format(os.path.basename(p_dcp_folder)))


def tdcpb_check(p_dcp_folder, p_check_type=u"short"):

    if (p_check_type == u"short"):
        tdcpb_check_short(p_dcp_folder)

    elif (p_check_type == u"long"):
        tdcpb_check_long(p_dcp_folder)
    else:
        _err = "unknow verfication type:{}".format(p_check_type)
        logger.error(_err)
        raise TdcpbException(_err)



