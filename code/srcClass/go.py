"""Extension of utilities.py to provide functions required to check the
version information of go and determine if it needs to be updated.

Classes:
    Go: extends the SrcClass class and provides the static variables and
        go specific functions required to perform a check on go.

Functions:
    get_SrcClass: returns a Go object
    main: runs compare_versions (see utilities.py) on a Go object
"""
from check_utilities import SrcClass, compare_versions
import urllib.request
import re
import time
import os
import json
import csv
import config_utilities as cf

def get_SrcClass(args):
    """Returns an object of the source class.

    This returns an object of the source class to allow access to its functions
    if the module is imported.
    
    Args:
    
    Returns:
        class: a source class object
    """
    return Go(args)

class Go(SrcClass):
    """Extends SrcClass to provide go specific check functions.

    This Go class provides source-specific functions that check the go version
    information and determine if it differs from the current version in the
    Knowledge Network (KN).

    Attributes:
        see utilities.SrcClass
    """
    def __init__(self, args=cf.config_args()):
        """Init a Stringdb with the staticly defined parameters.

        This calls the SrcClass constructor (see utilities.SrcClass)
        """
        name = 'go'
        url_base = 'http://geneontology.org/gene-associations/'
        aliases = {
            "fb": "Drosophila melanogaster",
            "goa_human": "Homo sapiens",
            "mgi": "Mus musculus",
            "obo_map": "ontology",
            "sgd": "Saccharomyces cerevisiae",
            "tair": "Arabidopsis thaliana",
            "wb": "Caenorhabditis elegans"
        }
        super(Go, self).__init__(name, url_base, aliases, args)

    def get_source_version(self, alias):
        """Return the release version of the remote go:alias.

        This returns the release version of the remote source for a specific
        alias. This value will be 'unknown' for every alias. This value is
        stored in the self.version dictionary object.

        Args:
            alias (str): An alias defined in self.aliases.

        Returns:
            str: The remote version of the source.
        """
        return super(Go, self).get_source_version(alias)

    def get_local_file_info(self, alias):
        """Return a dictionary with the local file information for the alias.

        (See utilities.SrcClass.get_local_file_info)

        Args:
            alias (str): An alias defined in self.aliases.

        Returns:
            dict: The local file information for a given source alias.
        """
        return super(Go, self).get_local_file_info(alias)

    def get_remote_file_size(self, alias):
        """Return the remote file size.

        This builds a url for the given alias (see get_remote_url) and then
        calls the SrcClass function (see
        utilities.SrcClass.get_remote_file_size).

        Args:
            alias (str): An alias defined in self.aliases.

        Returns:
            int: The remote file size in bytes.
        """
        url = self.get_remote_url(alias)
        return super(Go, self).get_remote_file_size(url)

    def get_remote_file_modified(self, alias):
        """Return the remote file date modified.

        This returns the date modified of the remote file for the given alias.

        Args:
            alias (str): An alias defined in self.aliases.

        Returns:
            float: time of last modification time of remote file in seconds
                since the epoch
        """
        if alias == 'obo_map':
            return float(0)
        url_download_page = ('http://geneontology.org/gene-associations/'
                             'go_annotation_metadata.all.js')
        response = urllib.request.urlopen(url_download_page)
        cur_id = ''
        ret_str = float(0)
        t_format = "%m/%d/%Y"
        for line in response:
            d_line = line.decode()
            alias_match = re.search(r'"id": "(\S+)",', d_line)
            if alias_match is not None:
                if alias_match.group(1) == alias:
                    cur_id = alias
                else:
                    cur_id = ''
            date_match = re.search(r'"submissionDate": "(\S+)"', d_line)
            if (date_match is not None) and (cur_id == alias):
                t_str = date_match.group(1)
                ret_str = time.mktime(time.strptime(t_str, t_format))
                break
        response.close()
        return ret_str

    def get_remote_url(self, alias):
        """Return the remote url needed to fetch the file corresponding to the
        alias.

        This returns the url needed to fetch the file corresponding to the
        alias. The url is constructed using the base_url and alias information.

        Args:
            alias (str): An alias defined in self.aliases.

        Returns:
            str: The url needed to fetch the file corresponding to the alias.
        """
        url = self.url_base + 'gene_association.' + alias + '.gz'
        # format for ontology information
        if alias == 'obo_map':
            url = 'http://purl.obolibrary.org/obo/go.obo'
        return url

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
        return super(Go, self).is_map(alias)

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
        return super(Go, self).get_dependencies(alias)

    def create_mapping_dict(self, filename):
        """Return a mapping dictionary for the provided file.

        This returns a dictionary for use in mapping nodes or edge types from
        the file specified by filetype. By default it opens the file specified
        by filename creates a dictionary using the first column as the key and
        the second column as the value.

        Args:
            filename(str): The name of the file containing the information
                needed to produce the maping dictionary.

        Returns:
            dict: A dictionary for use in mapping nodes or edge types.
        """
        term_map = dict()
        is_term = False
        with open(filename) as infile:
            for line in infile:
                if line.startswith('[Term]'):
                    line = infile.readline()
                    if not line.startswith('id: '):
                        continue
                    key = line[4:].strip()
                    line = infile.readline()
                    if not line.startswith('name: '):
                        continue
                    term_map[key] = line[6:].strip()
        return term_map

    def table(self, rawline, version_dict):
        """Uses the provided rawline file to produce a 2table_edge file, an
        edge_meta file, and a node_meta file (only for property nodes).

        This returns noting but produces the 2table formatted files from the
        provided rawline file:
            rawline table (file, line num, line_chksum, rawline)
            2tbl_edge table (line_cksum, n1name, n1hint, n1type, n1spec,
                            n2name, n2hint, n2type, n2spec, et_hint, score)
            edge_meta (line_cksum, info_type, info_desc)
            node_meta (line_cksum, node_num (1 or 2),
                       info_type (evidence, relationship, experiment, or link),
                       info_desc (text))

        Args:
            rawline(str): The path to the rawline file
            version_dict (dict): A dictionary describing the attributes of the
                alias for a source.

        Returns:
        """

        #outfiles
        table_file = rawline.replace('rawline','edge')
        n_meta_file = rawline.replace('rawline','node_meta')
        e_meta_file = rawline.replace('rawline','edge_meta')

        #static column values
        alias = version_dict['alias']
        source = version_dict['source']
        n1type = 'property'
        n1spec = '0'
        n1hint = source + '_' + alias
        n2type = 'gene'
        n2hint = 'UniProt/Ensembl_GeneID'
        score = 1
        
        node_num = 1
        info_type = 'synonym'
        info_type1 = 'reference'
        info_type2 = 'evidence'

        #mapping files
        obo_file = os.path.join('..', 'obo_map', 'go.obo_map.json')
        with open(obo_file) as infile:
            obo_map = json.load(infile)

        with open(rawline, encoding='utf-8') as infile, \
            open(table_file, 'w') as edges,\
            open(n_meta_file, 'w') as n_meta,\
            open(e_meta_file, 'w') as e_meta:
            reader = csv.reader(infile, delimiter='\t')
            edge_writer = csv.writer(edges, delimiter='\t')
            n_meta_writer = csv.writer(n_meta, delimiter='\t')
            e_meta_writer = csv.writer(e_meta, delimiter='\t')
            for line in reader:
                chksm = line[2]
                raw = line[3:]   
                
                # skip commented lines
                comment_match = re.match('!', raw[0])
                if comment_match is not None:
                    continue
                
                qualifier = raw[3]
                # skip "NOT" annotations
                not_match = re.search('NOT', qualifier)
                if not_match is not None:
                    continue
                
                n1_ID = raw[4]
                n1_orig_name = obo_map.get(n1_ID, "unmapped:no-name")
                n1 = 'go_' + re.sub('[^a-zA-Z0-9]','_',n1_orig_name)[0:35]
                
                n2 = raw[1]
                n2spec_str = raw[12].split("|",1)[0].rstrip() #only take first species
                n2spec = int(n2spec_str.split(":",1)[1]) #remove label taxon:

                reference = raw[5]
                anno_evidence = raw[6]

                et_hint = 'go_curated_evidence'
                if anno_evidence == 'IEA':
                    et_hint = 'go_inferred_evidence'
                    
                edge_writer.writerow([chksm, n1, n1hint, n1type, n1spec, \
                    n2, n2hint, n2type, n2spec, et_hint, score])
                n_meta_writer.writerow([chksm, node_num, info_type, n1_orig_name])
                e_meta_writer.writerow([chksm, info_type1, reference])
                e_meta_writer.writerow([chksm, info_type2, anno_evidence])


if __name__ == "__main__":
    """Runs compare_versions (see utilities.compare_versions) on a Go object.

    This runs the compare_versions function on a Go object to find the version
    information of the source and determine if a fetch is needed. The version
    information is also printed.

    Returns:
        dict: A nested dictionary describing the version information for each
            alias described in Go.
    """
    compare_versions(Go())