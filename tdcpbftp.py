#!/usr/bin/python
# -*- coding: utf-8 -*-
# -*- Mode: Python -*-
# vim:si:ai:et:sw=4:sts=4:ts=4

import sys
import logging
import argparse
import os.path

from common import parseConfig
from common import TdcpbException
from common import create_logger
from lftp   import Lftp

logger = create_logger()
CONFIG_FILE="/home/nicolas/tmp//exec-done.json"

def main(argv):
    parser = argparse.ArgumentParser(description='Copy DCP via FTP')
    parser.add_argument('dir_path',
        metavar='DIRECTORY_PATH',
        type = str,
        help = 'directory to copy / mirror ' )
    parser.add_argument('-d', '--debug', dest='debug', action='store_const',
        const=logging.DEBUG, default=logging.INFO,
        help='debug mode')
    parser.add_argument('-c', '--config',
        type = str,
        default = CONFIG_FILE,
        help='path to config file')
    parser.add_argument('-x', '--dry-run',
        type = bool,
        help='run ftp in dry run mode')



    args = parser.parse_args()

    try :
        config_data = parseConfig(args.config)
    except ValueError as err:
        msg = "JSON parse ERROR {}".format(err)
        logger.error(msg)
        return 1

    if not os.path.exists(args.dir_path):
        _err = "path {} does not exists".format(args.dir_path)
        logging.error(_err)
        return 1

    if 'ftp-library' in config_data and config_data['ftp-library'] == True :
        _dir_path = os.path.abspath(args.dir_path)
        try:

            ftp = Lftp(_dir_path, config_data)
            ftp.mirror()
        except TdcpbException as err :
            #smoething goes wrong in copy
            logger.error("FTP transfer FAIL: {}".format(err))
        else:
            logger.info("FTP transfer OK")



if __name__ == "__main__":
   sys.exit(main(sys.argv))


