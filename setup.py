#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- mode: python -*-
# vim:si:ai:et:sw=4:sts=4:ts=4
from distutils.core import setup

setup(
    name         = "tdcpb_tools",
    description  = "colletion of toools for tdcpb: ingets, verify, transmission post exec",
    author       = "Nicolas Bertrand",
    author_email = "nicolas@indecp.org",
    version      = "0.52",
    scripts      = [
        "bin/tdcpbftp",
        "bin/tdcpb-checkdcp-short",
        "bin/tdcpb-checkdcp-long",
        "bin/tdcpb-make-torrent",
        "bin/tdcpb-transmission-done",
        "bin/tdcpb-remove-torrent",
        "bin/tdcpb-detect-disk-overload"
                   ],
    packages    = ["tdcpblib"]
)
