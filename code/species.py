"""Extension of utilities.py to provide functions required to check the
version information of species and determine if it needs to be updated.

Classes:
    Species: Extends the SrcClass class and provides the static variables and
        species specific functions required to perform a check on species.

Functions:
    get_SrcClass: returns an Species object
    main: runs compare_versions (see utilities.py) on a Species object
"""
from utilities import SrcClass, compare_versions
import time
import ftplib

def get_SrcClass():
    """Returns an object of the source class.

    This returns an object of the source class to allow access to its functions
    if the module is imported.
    
    Args:
    
    Returns:
        class: a source class object
    """
    return Species()

class Species(SrcClass):
    """Extends SrcClass to provide species specific check functions.

    This Species class provides source-specific functions that check the
    species version information and determine if it differs from the current
    version in the Knowledge Network (KN).

    Attributes:
        see utilities.SrcClass
    """
    def __init__(self):
        """Init a Species with the staticly defined parameters.

        This calls the SrcClass constructor (see utilities.SrcClass)
        """
        name = 'species'
        url_base = 'ftp.ncbi.nih.gov'
        aliases = {"species_map": "mapping file for species"}
        super(Species, self).__init__(name, url_base, aliases)
        self.remote_file = 'nodes.dmp'

    def get_source_version(self, alias):
        """Return the release version of the remote species:alias.

        This returns the release version of the remote source for a specific
        alias. This value will be the same for every alias and is 'unknown' in
        this case. This value is stored in the self.version dictionary object.

        Args:
            alias (str): An alias defined in self.aliases.

        Returns:
            str: The remote version of the source.
        """
        return super(Species, self).get_source_version(alias)

    def get_local_file_info(self, alias):
        """Return a dictionary with the local file information for the alias.

        (See utilities.get_local_file_info)

        Args:
            alias (str): An alias defined in self.aliases.

        Returns:
            dict: The local file information for a given source alias.
        """
        return super(Species, self).get_local_file_info(alias)

    def get_remote_file_size(self, alias):
        """Return the remote file size.

        This builds a url for the given alias (see get_remote_url) and then
        calls the SrcClass function (see utilities.get_remote_file_size).

        Args:
            alias (str): An alias defined in self.aliases.

        Returns:
            int: The remote file size in bytes.
        """
        ftp = ftplib.FTP(self.url_base)
        ftp.login()
        ftp.cwd('/pub/taxonomy/')
        ftp.voidcmd('TYPE I')
        file_size = ftp.size('taxdmp.zip')
        ftp.quit()
        return file_size

    def get_remote_file_modified(self, alias):
        """Return the remote file date modified.

        This builds a url for the given alias (see get_remote_url) and then
        calls the SrcClass function (see utilities.get_remote_file_modified).

        Args:
            alias (str): An alias defined in self.aliases.

        Returns:
            float: time of last modification time of remote file in seconds
                since the epoch
        """
        ftp = ftplib.FTP(self.url_base)
        ftp.login()
        ftp.cwd('/pub/taxonomy/')
        time_str = ftp.sendcmd('MDTM taxdmp.zip')
        time_str = time_str[4:]
        ftp.quit()
        time_format = "%Y%m%d%H%M%S"
        return time.mktime(time.strptime(time_str, time_format))

    def get_remote_url(self, alias):
        """Return the remote url needed to fetch the file corresponding to the
        alias.

        This returns the url needed to fetch the file corresponding to the
        alias. The url is constructed using the base_url, alias, and source
        version information.

        Args:
            alias (str): An alias defined in self.aliases.

        Returns:
            str: The url needed to fetch the file corresponding to the alias.
        """
        url = self.url_base + '/pub/taxonomy/taxdmp.zip'
        return 'ftp://' + url

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
        return super(Species, self).is_map(alias)

    def get_dependencies(self, alias):
        """Return a list of other aliases that the provided alias depends on.

        This returns a list of other aliases that must be processed before
        full processing of the provided alias can be completed.

        Args:
            alias(str): An alias defined in self.aliases.

        Returns:
            list: The other aliases defined in self.aliases that the provided
            alias depends on.
        """
        return super(Species, self).get_dependencies(alias)

if __name__ == "__main__":
    """Runs compare_versions (see utilities.compare_versions) on a species
    object

    This runs the compare_versions function on a species object to find the
    version information of the source and determine if a fetch is needed. The
    version information is also printed.

    Returns:
        dict: A nested dictionary describing the version information for each
            alias described in species.
    """
    compare_versions(Species())
