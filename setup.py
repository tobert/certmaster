#!/usr/bin/python

from distutils.core import setup
#from setuptools import setup,find_packages

NAME = "certmaster"
VERSION = open("version", "r+").read().split()[0]
SHORT_DESC = "%s remote configuration and management api" % NAME
LONG_DESC = """
A small pluggable xml-rpc daemon used by %s to implement various web services hooks
""" % NAME


if __name__ == "__main__":
 
        manpath    = "share/man/man1/"
        etcpath    = "/etc/%s" % NAME
        initpath   = "/etc/init.d/"
        logpath    = "/var/log/%s/" % NAME
	certdir    = "/var/lib/%s/" % NAME
        pkipath    = "/etc/pki/%s" % NAME
        rotpath    = "/etc/logrotate.d"
        aclpath    = "%s/minion-acl.d" % etcpath
        setup(
                name="%s" % NAME,
                version = VERSION,
                author = "Lots",
                author_email = "certmaster-list@redhat.com",
                url = "https://hosted.fedoraproject.org/projects/certmaster/",
                license = "GPL",
		scripts = [
                     "scripts/certmaster", "scripts/certmaster-ca",
                     "scripts/certmaster-request",
                ],
		# package_data = { '' : ['*.*'] },
                package_dir = {"%s" % NAME: "%s" % NAME
                },
		packages = ["%s" % NAME,
	        	    "%s/minion" % NAME,
			    "%s/overlord" % NAME,
                ],
                data_files = [(initpath, ["init-scripts/certmaster"]),
                              (etcpath,  ["etc/minion.conf"]),
                              (etcpath,  ["etc/certmaster.conf"]),
                              (manpath,  ["docs/certmaster.1.gz"]),
                              (manpath,  ["docs/certmaster-request.1.gz"]),
                              (manpath,  ["docs/certmaster-ca.1.gz"]),
			      (rotpath,  ['etc/certmaster_rotate']),
                              (logpath,  []),
			      (certdir,  []),
			      (etcpath,  []),
			      (pkipath,  []),
			      (aclpath,  [])
                ],
                description = SHORT_DESC,
                long_description = LONG_DESC
        )

