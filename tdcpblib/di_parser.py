#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Mode: Python -*-
# vim:si:ai:et:sw=4:sts=4:ts=4
#
#
# Copyright Nicolas Bertrand (nico@isf.cc), 2013
#
# This file is part of DcpIngest.
#
#    DcpIngest is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Luciole is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Luciole.  If not, see <http://www.gnu.org/licenses/>.
#
#
#
# ref document :
#   SMPTE 429-9-2007 D-Cinema Packaging — Asset Mapping and File Segmentation
#   SMPTE 429-8-2007 D-Cinema Packaging — Packing List

import sys
import os.path
from lxml import etree
import logging
import hashlib
from functools import partial
from urlparse import urlparse

from common import TdcpbException

def list_all_files(p_path):
    fileList = []
    fileSize = 0
    folderCount = 0
    for root, subFolders, files in os.walk(p_path):
        folderCount += len(subFolders)
        # add empty folder to fileList
        for _folder in subFolders:
            _f = os.path.join(root,_folder)
            if not os.listdir(_f):
                fileList.append(_f)
        # add files
        for file in files:
            f = os.path.join(root,file)
            fileSize = fileSize + os.path.getsize(f)
            fileList.append(f)
    logging.debug("Total Size is {0} bytes".format(fileSize))
    logging.debug("Total Files: {} ".format(len(fileList)))
    logging.debug("Total Folders: {}".format(folderCount))
    # return relative path
    fileList = [ _w.split(p_path)[1] for _w in fileList]
    # remove leading "/"
    fileList = [ _w[1:] for _w in fileList]
    return sorted(fileList)

def URItoPath(p_path):
    _parsed = urlparse(p_path.strip())
    _abs_path = ''.join([_parsed.netloc, _parsed.path])
    if _abs_path.startswith("/"):
        #remove leading "/"
        _abs_path = _abs_path[1:]
    return _abs_path

class DiError(TdcpbException):
    def __init__(self,value):
        self.value= value
    def __str__(self):
        return repr(self.value)

class AssetmapParser(object):
    def __init__(self, p_xml_path):
        self.p_xml_path = p_xml_path
        try:
            self.tree = etree.parse(self.p_xml_path)
        except IOError, msg:
            _msg="Parser Error in file {}: {}".format(self.p_xml_path, msg)
            raise DiError(_msg)
        except etree.XMLSyntaxError ,_msg:
            _err = "File {}: {}".format(self.p_xml_path, _msg)
            raise DiError(_err)

        self.root = self.tree.getroot()
        self._GetNamespaces()
        self.assets = {}
        self._Verify()

    def Dump(self):
        pass

    def GetAllAssets(self) :
        _assets = self.tree.findall('./am:AssetList/am:Asset', namespaces = self.ns)
        for _asset in _assets:
            _id = _asset.find('am:Id', namespaces = self.ns)
            _path = _asset.find("./am:ChunkList/am:Chunk/am:Path", namespaces = self.ns)
            self.assets[_id.text] = URItoPath(_path.text)
        return self.assets

    def GetPkls(self) :
        self.pkls = []
        _assets = self.tree.findall('./am:AssetList/am:Asset', namespaces = self.ns)
        for _asset in _assets:
            _pkl = _asset.find('am:PackingList', namespaces = self.ns)
            if (_pkl is not None):
                if (_pkl.text != "false"):
                    self.pkls.append(_asset.find('am:Id', namespaces = self.ns).text)
        return self.pkls

    def _GetNamespaces(self):
        """ Get Namespaces """
        _ns = self.tree.getroot().tag[1:].split("}")[0]
        self.ns = {'am': _ns}
        logging.debug("Namespace is {}".format(self.ns))


    def _FindOne(self, p_tag, p_elem = None) :

        if p_elem is not None :
            _elem = p_elem.findall(p_tag, namespaces = self.ns)
        else :
            _elem = self.tree.findall(p_tag, namespaces = self.ns)
        if len( _elem) != 1:
            _emsg = "Find tag {} {} times. Exepcted only one.".format(p_tag,
                                                                      len(_elem))
            raise DiError(_emsg)
        return _elem[0]

    def _Verify(self):
        for _tag in self.root.findall('am:VolumeCount', namespaces = self.ns):
            _count = int(_tag.text)
            if _count > 1:
                _emsg = "The tool does not support more the one VOLINDEX"
                raise DiError(_emsg)

        _tag = './am:AssetList'
        _asset_list = self._FindOne(_tag)
        _tag = './am:Asset'
        _assets =_asset_list.findall(_tag, namespaces = self.ns)
        if not _assets:
            _emsg = "No Asset found. Invalid AssetMap"
            raise DiError(_emsg)

        _pkl_count = 0
        for _asset in _assets:
            # check Id presence
            _tag = './am:Id'
            _id = self._FindOne(_tag, _asset)
            _tag = './am:PackingList'
            _pkl =_asset.find(_tag, namespaces = self.ns)
            if (_pkl is not None):
                if (_pkl.text != "false"):
                    _pkl_count += 1
            _tag = './am:ChunkList'
            _chunk_list = self._FindOne(_tag, _asset)
            _tag = './am:Chunk'
            _chunk = _chunk_list.findall(_tag, namespaces = self.ns)
            if not _chunk :
                _emsg =" No Chunk found"
                raise DiError(_emsg)
            if len(_chunk) > 1 :
                _emsg = "Tool doesn't handle segmentation (i.e. several vol index)"
                raise DiError(_emsg)
            _tag = './am:Path'
            _path = self._FindOne(_tag, _chunk[0])
        if _pkl_count == 0 :
            _emsg = "No PKL found."
            raise DiError(_emsg)


class PklParser(AssetmapParser):

    def __init__(self,p_xml_path, pkl_urn_id):
        self.pkl_data={}
        self.pkl_urn_id = pkl_urn_id
        AssetmapParser.__init__(self,p_xml_path)

    def _GetNamespaces(self):
        """ Get Namespaces """
        _ns = self.tree.getroot().tag[1:].split("}")[0]
        self.ns = {'pkl': _ns}

    def GetAssets(self):
        _assets = self.tree.findall('./pkl:AssetList/pkl:Asset', namespaces = self.ns)
        for _asset in _assets:
            _asset_dict={}
            # parse mandatory tags
            _tag = 'Id'
            _id = _asset.find('pkl:{}'.format(_tag), namespaces = self.ns)

            _tag = 'Hash'
            _elem = _asset.find('pkl:{}'.format(_tag), namespaces = self.ns)
            _asset_dict[_tag] = _elem.text

            _tag = 'Size'
            _elem = _asset.find('pkl:{}'.format(_tag), namespaces = self.ns)
            _asset_dict[_tag] = _elem.text

            _tag = 'Type'
            _elem = _asset.find('pkl:{}'.format(_tag), namespaces = self.ns)
            _asset_dict[_tag] = _elem.text

            # parse optional tags
            _tag = 'OriginalFileName'
            _elem = _asset.find('pkl:{}'.format(_tag), namespaces = self.ns)
            if _elem is not None:
                _asset_dict[_tag] = _elem.text

            _tag = 'AnnotationText'
            _elem = _asset.find('pkl:{}'.format(_tag), namespaces = self.ns)
            if _elem is not None:
                _asset_dict[_tag] = _elem.text
            self.assets[_id.text] = _asset_dict
        return self.assets

    def DumpPkl(self):
        if self.pkl_data is None:
            return
        _pkl_str="Packing List data\n"
        _tag = "Id"
        _pkl_str += "{:<30}: {}\n".format(_tag, self.pkl_data[_tag])
        _tag = "IssueDate"
        _pkl_str += "{:<30}: {}\n".format(_tag, self.pkl_data[_tag])
        _tag = "Issuer"
        _pkl_str += "{:<30}: {}\n".format(_tag, self.pkl_data[_tag])
        _tag = "Creator"
        _pkl_str += "{:<30}: {}\n".format(_tag, self.pkl_data[_tag])
        print _pkl_str

    def _Verify(self):
        _tag = 'Id'
        self.pkl_data[_tag] = self._FindOne('./pkl:{}'.format(_tag)).text
        if self.pkl_data[_tag] != self.pkl_urn_id:
            _msg = "Id of PKL did not match one in AssetMap"
            logging.error("ID in PKL: {} ID of PKL in AssetMap: {}".format(
                self.pkl_data[_tag], self.pkl_urn_id))
            raise DiError, _msg
        _tag = 'IssueDate'
        self.pkl_data[_tag] = self._FindOne('./pkl:{}'.format(_tag)).text
        _tag = 'Issuer'
        self.pkl_data[_tag] = self._FindOne('./pkl:{}'.format(_tag)).text
        _tag = 'Creator'
        self.pkl_data[_tag] = self._FindOne('./pkl:{}'.format(_tag)).text

        _tag = 'AssetList'
        self._FindOne('./pkl:{}'.format(_tag))

class DiParser(object):


    def __init__(self, p_dcp_folder):
        if os.path.exists(p_dcp_folder):
            self.p_dcp_folder = p_dcp_folder
        else:
            _emsg = "Not a DCP folder: {}".format(p_dcp_folder)
            raise DiError(_emsg)
        self.volindex = ""

    def list_dcp_files(self):
        try:
            self.getAssetmap()
            self._assetmap_xml = AssetmapParser(self.assetmap_path)
        except DiError, msg:
            logging.error(msg)
            return 0
        self.am_assets = self._assetmap_xml.GetAllAssets()
        _dcp_files = list(self.am_assets.viewvalues())
        # insert assetmap file
        _dcp_files.append(os.path.basename(self.assetmap_path))
        # insert VOLINDEX as it is not listed in AssetMap
        # TODO Manage case of several VOLINDEX ie with or without .xml
        _dcp_files.append(self.volindex)
        return sorted(_dcp_files)

    def check_files(self):
        _nb_assets = 0
        # 1st check presence of dummy VOLINDEX
        if not self.isVolindexPresent():
            _msg = "No VOLINDEX found in DCP folder({}) ".format(
                self.p_dcp_folder)
            logging.error(_msg)
            return 0
        try:
            self.getAssetmap()
            self._assetmap_xml = AssetmapParser(self.assetmap_path)
        except DiError, msg:
            logging.error(msg)
            return 0
        self.am_assets = self._assetmap_xml.GetAllAssets()
        logging.debug("Found {} assets".format(len(self.am_assets)))
        self.pkls = self._assetmap_xml.GetPkls()
        logging.debug("Found {} PKLS".format(len(self.pkls)))
        if len(self.pkls) == 0:
            _msg = "No PKL found. Bad DCP"
            logging.error(_msg)
            return 0
        for _pkl in self.pkls :
            _pkl_urn_id = _pkl
            _pkl_path= os.path.join(self.p_dcp_folder, self.am_assets[_pkl_urn_id])
            logging.debug("Parsing PKL: {}".format(os.path.basename(_pkl_path)))
            try:
                _pkl_xml = PklParser(_pkl_path, _pkl_urn_id)
            except DiError, msg:
                logging.error(msg)
                return 0
            # Valid pkl file increasse asset counter
            _nb_assets +=1
            _msg = "Found : {} ".format(self.am_assets[_pkl_urn_id])
            logging.debug(_msg)

            _pkl_assets = _pkl_xml.GetAssets()
            try:
                _nb_assets += self._ExistsAssets(_pkl_assets)
            except DiError, _msg:
                logging.error(_msg)
                return 0
            if (_nb_assets != len (self.am_assets)):
                _msg = "Invalid number of assets,( {} in AssetMap, {} counted)"\
                    .format(len(self.am_assets), _nb_assets)

        # check presence of uneeded files
        _dcp_files = self.list_dcp_files()
        _dir_files = list_all_files(self.p_dcp_folder)
        if len(_dir_files) > len(_dcp_files):
            logging.error("Unexpected files or dir present in DCP folder {}"\
                .format(self.p_dcp_folder))
            _unexpected = list(set(_dir_files) - set(_dcp_files))
            logging.error("Unexpected files or dir : ")
            for _f in _unexpected: 
                logging.error("   {}".format(_f))
 
            logging.error("Files in directory = {} Excpected files in DCP = {}".\
                    format(len(_dir_files), len(_dcp_files)))
            return 0
        elif len(_dir_files) < len(_dcp_files):
            _msg="DCP {} contains less file then expected : files in dir = {} expected fils ={} "\
                .format(self.p_dcp_folder, len(_dir_files),  len(_dcp_files) )
            logging.error(_msg)
            return 0
        else :
            logging.debug("files in DCP and files in Assetmap are coherent")

        return _nb_assets

    def check_hash(self):
        _nb_assets = 0
        # 1st check presence of dummy VOLINDEX
        if not self.isVolindexPresent():
            _msg = "No VOLINDEX found in DCP folder({}) ".format(
                self.p_dcp_folder)
            logging.error(_msg)
            return "KO"
        try:
            self.getAssetmap()
            self._assetmap_xml = AssetmapParser(self.assetmap_path)
        except DiError, msg:
            logging.error(msg)
            return "KO"
        self.am_assets = self._assetmap_xml.GetAllAssets()
        logging.debug("Found {} assets".format(len(self.am_assets)))
        self.pkls = self._assetmap_xml.GetPkls()
        if len(self.pkls) == 0:
            _msg = "No PKL found. Bad DCP"
            logging.error(_msg)
            return "KO"
        for _pkl in self.pkls :
            _pkl_urn_id = _pkl
            _pkl_path= os.path.join(self.p_dcp_folder, self.am_assets[_pkl_urn_id])
            logging.debug("Parsing PKL: {}".format(os.path.basename(_pkl_path)))
            try:
                _pkl_xml = PklParser(_pkl_path, _pkl_urn_id)
            except DiError, msg:
                logging.error(msg)
                return "KO"
            # Valid pkl file increasse asset counter
            _nb_assets +=1
            _msg = "Found : {} ".format(self.am_assets[_pkl_urn_id])
            logging.debug(_msg)

            _pkl_assets = _pkl_xml.GetAssets()
            try:
                self._ExistsAssets(_pkl_assets)
                self._VerifyHash()
            except DiError, _msg:
                logging.error(_msg)
                return "KO"
        return "OK"


    def Ingest(self):
        self.getAssetmap()
        self._assetmap_xml = AssetmapParser(self.assetmap_path)
        self.am_assets = self._assetmap_xml.GetAllAssets()
        self.pkls = self._assetmap_xml.GetPkls()
        for _pkl in self.pkls:
            _pkl_path= os.path.join(self.p_dcp_folder, self.am_assets[_pkl])
            _pkl_xml = PklParser(_pkl_path)
            _pkl_assets = _pkl_xml.GetAssets()
            _pkl_xml.DumpPkl()
            self._VerifyAssets(_pkl_assets)

    def getAssetmap(self) :
        _assetmap = os.path.join(self.p_dcp_folder, "ASSETMAP")
        if os.path.isfile(_assetmap):
            logging.debug("The DCP is in interop format")
            self.assetmap_path = _assetmap
        else:
            _assetmap = os.path.join(self.p_dcp_folder, "ASSETMAP.xml")
            if os.path.isfile(_assetmap):
                logging.debug("The DCP is in SMPTE format")
                self.assetmap_path = _assetmap
            else:
                _emsg="No ASSETMAP file found"
                raise DiError(_emsg)
        return

    def isAssetmap(self, p_file):
        if (p_file == "ASSETMAP") or (p_file == "ASSETMAP.xml"):
            return True
        return False

    def isVolindexPresent(self):
        if os.path.exists(os.path.join(self.p_dcp_folder, "VOLINDEX")):
            self.volindex = "VOLINDEX"
            return True
        if os.path.exists(os.path.join(self.p_dcp_folder, "VOLINDEX.xml")) :
            self.volindex = "VOLINDEX.xml"
            return True
        return False

    def _ExistsAssets(self, p_pkl_assets):
        self.assets = {}
        for _k,_v in p_pkl_assets.iteritems():
            if _k in self.am_assets:
                _asset =_v
                _path = os.path.join(self.p_dcp_folder, self.am_assets[_k])
                if os.path.exists(_path):
                    _asset['Path'] = _path
                    _msg = "Found : {} ".format(_path[len(self.p_dcp_folder):])
                    logging.debug(_msg)
                else:
                    _msg = "Asset {} not in DCP directory".format(
                        _path[len(self.p_dcp_folder):])
                    raise DiError(_msg)
                if os.stat(_path).st_size != int(_v['Size']) :
                    _msg = "Asset {} has wrong size".format(
                        _path[len(self.p_dcp_folder):])
                    logging.error("stat size = {}, Size in PKL = {}".format(
                        os.stat(_path).st_size, _v['Size']))
                    raise DiError(_msg)
                self.assets[_k] = _asset
            else:
                _msg = "Asset with id {} not found in assetmap".format(_k)
                raise DiError(_msg)
        return len(self.assets)

    def _VerifyHash(self):
        for _k, _v in self.assets.iteritems():
            _msg = "Checking hash of {}".format(_v['Path'])
            logging.debug(_msg)
            _sum = self._HashSum(_v['Path'])
            if _sum == _v['Hash']:
                _msg = " Hash verification OK ({})".format(_v['Path'])
                logging.debug(_msg)
            else:
                _msg = " Hash verification failed for file {} \
CALC SUM = {}\n EXPT SUM = {} ".format( _v['Path'], _sum, _v['Hash'] )
                logging.error(_msg)
                raise DiError(_msg)

    def _HashSum(self, p_filepath):
        """ check SHA1 of DCP files.
            As defined in SMPTE 429-8-2007 section 6.3"""
        _sha1 = hashlib.sha1()
        _f = open(p_filepath, 'rb')
        try:
            for _buff in iter(partial(_f.read, 10 * 1024**2), ''):
                _sha1.update(_buff)
        finally:
            _f.close()
        return _sha1.digest().encode('base64').strip()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    DCP = DiParser(sys.argv[1])
    dcp_files = DCP.list_dcp_files()
    print dcp_files
