#!/usr/bin/python
# -*- coding: utf-8 -*-
# -*- Mode: Python -*-
# vim:si:ai:et:sw=4:sts=4:ts=4
import sys
import os.path
import re
import subprocess as SP
from common import TdcpbException
from . import logger


class Lftp(object):
    LFTP_CMDS="set xfer:log true; set net:reconnect-interval-base 20; set net:max-retries 2; mirror --verbose=3 -Rcp {dry_run} {local} {remote} ; quit"
    #LFTP_CMDS="set xfer:log true; mirror --verbose=1 -Rc {local} {remote} {dry_run} ; quit"
    LFTP_SSL_CMDS=\
    "set ftp:ssl-force true; set ssl:verify-certificate no; set xfer:log true;  mirror --verbose=3 -Rcp {dry_run} {local} {remote} ; quit"

    def __init__(self, p_dir_path, p_config_data, dry_run = False ) :
        self.config_data = p_config_data
        # TODO verfiy p_dir_path
        self.dir_path = p_dir_path
        if 'ftp-ssl' in self.config_data and self.config_data['ftp-ssl'] == True:
            lftp_tpl = self.LFTP_SSL_CMDS
        else:
            lftp_tpl = self.LFTP_CMDS
        try:
            if self.config_data['ftp-remote-path'] is None:
                logger.error('No remote path specified')
                _msg=u"No remote path specified', please verify".format(self.config_data['ftp-remote-path'])
                raise TdcpbException(_msg)
            if self.config_data['ftp-remote-path'] == "/":
                lftp_cmd = lftp_tpl.format(local = self.dir_path , remote='', dry_run='')
            else:
                if not (self.config_data['ftp-remote-path']).endswith("/"):
                    _msg=u"ftp-remote-path({}) shall ends with /, please verify".format(self.config_data['ftp-remote-path'])
                    raise TdcpbException(_msg)
                lftp_cmd = lftp_tpl.format( local = self.dir_path,
                                            remote = self.config_data['ftp-remote-path'],
                                            dry_run='')
            _ftp_connect="ftp://{}:{}@{}".format(self.config_data['ftp-user'],
                                                 self.config_data['ftp-pass'],
                                                 self.config_data['ftp-host'])
            self.cmd = ["lftp",
                _ftp_connect,
                "-e",
                lftp_cmd
                ]
            self.my_env =os.environ
            self.my_env["LC_ALL"]="C"

            logger.debug("Cmd: {}".format(" ".join(self.cmd)))
        except KeyError as err:
            msg = "KEY ERROR for {}".format(err)
            logger.error(msg)
            raise TdcpbException(msg)

    def mirror(self):
        logger.info("Starting FTP copy of {}".format(os.path.basename(self.dir_path)))
        retry = False
        try :
            self.run_lftp()
        except TdcpbException as _err:
            retry = True
        else:
            logger.info("Copy of {} successfull".format(os.path.basename(self.dir_path)))

        if retry:
            logger.warning("Retrying mirror cmd via lftp")
            try :
                self.run_lftp()
            except TdcpbException as _err:
                logger.error("Copy of {} FAILED".format(os.path.basename(self.dir_path)))
                raise TdcpbException(_err)
            else:
                logger.info("Copy of {} successfull".format(os.path.basename(self.dir_path)))



    def is_data_tansfered(self, stdout):
        if "\nNew:" in stdout:
            p =re.compile('\d+ bytes transferred')
            res = p.search(stdout)
            if res:
                p2 =re.compile('\d+')
                res2 = p2.search(res.group())
                if res2:
                    return int(res2.group())
            # if "New" found and not found number od transfered by return invalid
            return -1
        return 0

    def run_lftp(self):
        nb_data = -1
        sync = SP.Popen(self.cmd, env= self.my_env, stdout = SP.PIPE, stderr = SP.PIPE)
        (stdout, stderr) = sync.communicate()
        logger.debug("STDOUT")
        logger.debug("\n{}".format(stdout))
        logger.debug("END STDOUT")
        logger.debug("return code: {}".format(sync.returncode))
        if sync.returncode == 0:
            nb_data=self.is_data_tansfered(stdout)
            if (nb_data > 0) :
                logger.info(u"{} bytes transfered to library".format(nb_data))
            elif nb_data == 0:
                logger.info(u"No new data transfered")
            else:
                _msg="Invalid inyterpreatation of stdout \n:{}".format(stdout)
                raise TdcpbException(_msg)
        elif sync.returncode:
            _msg = "FTP command failed returncode= {} ".format(sync.returncode)
            logger.error(_msg)
            logger.error(stderr)
            raise TdcpbException(_msg)
        return nb_data



