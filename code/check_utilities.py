"""Utiliites for checking if a source needs to be updated in the Knowledge
Network (KN).

Classes:
    SrcClass: Extends the object class and serves as the base class for each
        supported source in the KN.

Functions:
    get_SrcClass: returns a SrcClass object
    compare_versions(SrcClass) -> dict: takes a SrcClass object and returns a
        dictionary containing the most recent file version information and if
        a fetch is required

Variables:
    DIR: relative path to the raw_download folder from location of script
        execution
"""

import urllib.request
import os
import time
import json
import csv

DIR = os.path.join('..', 'raw_downloads')

def get_SrcClass():
    """Returns an object of the source class.

    This returns an object of the source class to allow access to its functions
    if the module is imported.
    
    Args:
    
    Returns:
        class: a source class object
    """
    return SrcClass()

class SrcClass(object):
    """Base class to be extended by each supported source in KnowEnG.

    This SrcClass provides default functions that should be extended
    or overridden by any source which is added to the Knowledge Network (KN).

    Attributes:
        name (str): The name of the remote source to be included in the KN.
        url_base (str): The base url of the remote source, which may need
            additional processing to provide an actual download link (see
            get_remote_url).
        aliases (dict): A dictionary with subsets of the source which will be
            included in the KN  as the keys (e.g. different species, data
            types, or interaction types), and a short string with information
            about the alias as the value.
        remote_file (str): The name of the file to extract if the remote source
            is a directory
        version (dict): The release version of each alias in the source.
    """

    def __init__(self, src_name, base_url, aliases):
        """Init a SrcClass object with the provided parameters.

        Constructs a SrcClass object with the provided parameters, which should
        be provided by any class extending SrcClass.

        Args:
            src_name (str): The name of the remote source to be included in
                the KN. Must be provided by the extending class.
            url_base (str): The base url of the remote source, which may need
                additional processing to provide an actual download link (see
                get_remote_url). Must be provided by the extending class.
            aliases (dict): A dictionary with subsets of the source which will
                be included in the KN  as the keys (e.g. different species,
                data types, or interaction types), and a short string with
                information about the alias as the value.
            version (dict): The release version of each alias in the source.
                Default empty dictionary if not provided by the extending
                class.
        """
        self.name = src_name
        self.url_base = base_url
        self.aliases = aliases
        self.remote_file = ''
        self.version = dict()

    def get_source_version(self, alias):
        """Return the release version of the remote source:alias.

        This returns the release version of the remote source for a specific
        alias. This value will be the same for every alias unless the
        the alias can have a different release version than the source
        (this will be source dependent). This value is stored in the
        self.version dictionary object. If the value does not already,
        all aliases versions are initialized to 'unknown'.

        Args:
            alias (str): An alias defined in self.aliases.

        Returns:
            str: The remote version of the source.
        """
        if alias not in self.version:
            for alias_name in self.aliases:
                self.version[alias_name] = 'unknown'
        return self.version[alias]

    def get_local_file_info(self, alias):
        """Return a dictionary with the local file information for the alias.

        This returns the local file information for a given source alias, which
        will always contain the following keys:
            'local_file_name' (str): name of the file locally
            'local_file_exists' (bool): boolean if file exists at path
                indicated by 'local_file_name'
        and will also conatin the following if 'local_file_exists' is True:
            'local_size' (int): size of local file in bytes
            'local_date' (float): time of last modification time of local file
                in seconds since the epoch

        Args:
            alias (str): An alias defined in self.aliases.

        Returns:
            dict: The local file information for a given source alias.
        """

        f_dir = os.path.join(DIR, self.name)
        f_dir = os.path.join(f_dir, alias)
        url = self.get_remote_url(alias)
        filename = os.path.basename(url)
        file = os.path.join(f_dir, filename)
        local_dict = dict()
        local_dict['local_file_name'] = filename
        local_dict['local_file_exists'] = os.path.isfile(file)
        if not local_dict['local_file_exists']:
            return local_dict
        local_dict['local_size'] = os.path.getsize(file)
        local_dict['local_date'] = os.path.getmtime(file)
        return local_dict

    def get_remote_file_size(self, remote_url):
        """Return the remote file size.

        This returns the remote file size as specificied by the
        'content-length' page header. If the remote file size is unknown, this
        value should be -1.

        Args:
            remote_url (str): The url of the remote file to get the size of.

        Returns:
            int: The remote file size in bytes.
        """
        try:
            response = urllib.request.urlopen(remote_url)
            return int(response.headers['content-length'])
        except:
            return -1

    def get_remote_file_modified(self, remote_url):
        """Return the remote file date modified.

        This returns the remote file date modifed as specificied by the
        'last-modified' page header.

        Args:
            remote_url (str): The url of the remote file to get the date
                modified of.

        Returns:
            float: time of last modification time of remote file in seconds
                since the epoch
        """
        try:
            response = urllib.request.urlopen(remote_url)
            time_str = response.headers['last-modified']
            time_format = "%a, %d %b %Y %H:%M:%S %Z"
            return time.mktime(time.strptime(time_str, time_format))
        except:
            return float(0)

    def get_remote_url(self, alias):
        """Return the remote url needed to fetch the file corresponding to the
        alias.

        This returns the url needed to fetch the file corresponding to the
        alias. By default this returns self.base_url.

        Args:
            alias (str): An alias defined in self.aliases.

        Returns:
            str: The url needed to fetch the file corresponding to the alias.
        """
        return self.url_base

    def is_map(self, alias):
        """Return a boolean representing if the provided alias is used for
        source specific mapping of nodes or edges.
        
        This returns a boolean representing if the alias corresponds to a file
        used for mapping. By default this returns True if the alias ends in
        '_map' and False otherwise.

        Args:
            alias(str): An alias defined in self.aliases.

        Returns:
            bool: Whether or not the alias is used for mapping.
        """
        if alias[-4:] == '_map':
            return True
        else:
            return False

    def get_dependencies(self, alias):
        """Return a list of other aliases that the provided alias depends on.

        This returns a list of other aliases that must be processed before
        full processing of the provided alias can be completed. By default,
        returns a list of all aliases which are considered mapping files (see
        is_map)

        Args:
            alias(str): An alias defined in self.aliases.

        Returns:
            list: The other aliases defined in self.aliases that the provided
                alias depends on.
        """
        depends = list()
        for alias_name in self.aliases:
            if alias_name == alias:
                continue
            elif self.is_map(alias_name):
                depends.append(alias_name)
        return depends

    def create_mapping_dict(self, filename, key_col=0, value_col=1):
        """Return a mapping dictionary for the provided file.

        This returns a dictionary for use in mapping nodes or edge types from
        the file specified by filetype. By default it opens the file specified
        by filename creates a dictionary using the key_col column as the key
        and the value_col column as the value.

        Args:
            filename(str): The name of the file containing the information
                needed to produce the maping dictionary.
            key_col(int): The column containing the key for creating the
                dictionary. By default this is column 0.
            value_col(int): The column containing the value for creating the
                dictionary. By default this is column 1.

        Returns:
            dict: A dictionary for use in mapping nodes or edge types.
        """
        alias = filename.split('.')[1]
        map_dict = dict()
        if not self.is_map(alias):
            return map_dict
        with open(filename, 'rb') as map_file:
            reader = csv.reader((line.decode('utf-8') for line in map_file), 
                delimiter='\t')
            for line in reader:
                map_dict[line[key_col]] = line[value_col]
        return map_dict

def compare_versions(src_obj):
    """Return a dictionary with the version information for each alias in the
    source and write a dictionary for each alias to file.

    This returns a nested dictionary describing the version information of each
    alias in the source. The version information is also printed. For each
    alias the following keys are defined:
        'source' (str): The source name
        'alias' (str): The alias name
        'alias_info' (str): A short string with information about the alias.
        'is_map' (bool): See is_map.
        'dependencies' (lists): See get_dependencies.
        'remote_url' (str): See get_remote_url.
        'remote_date' (float): See get_remote_file_modified.
        'remote_version' (str): See get_source_version.
        'remote_file' (str): File to extract if remote file location is a
            directory.
        'remote_size' (int): See get_remote_file_size.
        'local_file_name' (str): See get_local_file_info.
        'local_file_exists' (bool): See get_local_file_info.
        'fetch_needed' (bool): True if file needs to be downloaded from remote
            source. A fetch will be needed if the local file does not exist,
            or if the local and remote files have different date modified or
            file sizes.

    Args:
        src_obj (SrcClass): A SrcClass object for which the comparison should
            be performed.

    Returns:
        dict: A nested dictionary describing the version information for each
            alias described in src_obj.
    """
    version_dict = dict()
    local_dict = dict()
    for alias in src_obj.aliases:
        local_dict[alias] = src_obj.get_local_file_info(alias)
        version_dict[alias] = dict()
        version_dict[alias]['source'] = src_obj.name
        version_dict[alias]['alias'] = alias
        version_dict[alias]['alias_info'] = src_obj.aliases[alias]
        version_dict[alias]['is_map'] = src_obj.is_map(alias)
        version_dict[alias]['dependencies'] = src_obj.get_dependencies(alias)
        version_dict[alias]['remote_url'] = src_obj.get_remote_url(alias)
        version_dict[alias]['remote_file'] = src_obj.remote_file
        version_dict[alias]['remote_date'] = \
            src_obj.get_remote_file_modified(alias)
        version_dict[alias]['remote_version'] = \
            src_obj.get_source_version(alias)
        version_dict[alias]['remote_size'] = src_obj.get_remote_file_size(alias)
        version_dict[alias]['local_file_name'] = \
            local_dict[alias]['local_file_name']
        version_dict[alias]['local_file_exists'] = \
            local_dict[alias]['local_file_exists']

        if not local_dict[alias]['local_file_exists']:
            version_dict[alias]['fetch_needed'] = True
            continue

        l_size = local_dict[alias]['local_size']
        r_size = version_dict[alias]['remote_size']
        l_date = local_dict[alias]['local_date']
        r_date = version_dict[alias]['remote_date']

        if r_size != -1 and l_size != r_size:
            version_dict[alias]['fetch_needed'] = True
        elif r_date != 'unknown' and l_date < r_date:
            version_dict[alias]['fetch_needed'] = True
        elif r_size == -1 and r_date == 'unknown':
            version_dict[alias]['fetch_needed'] = True
        else:
            version_dict[alias]['fetch_needed'] = False

    f_dir = os.path.join(DIR, src_obj.name)
    os.makedirs(f_dir, exist_ok=True)
    for alias in src_obj.aliases:
        a_dir = os.path.join(f_dir, alias)
        os.makedirs(a_dir, exist_ok=True)
        f_name = os.path.join(a_dir, 'file_metadata.json')
        with open(f_name, 'w') as outfile:
            json.dump(version_dict[alias], outfile, indent=4, sort_keys=True)
    print(json.dumps(version_dict, indent=4, sort_keys=True))
    return version_dict