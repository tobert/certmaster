#!/usr/bin/python

from distutils.core import setup
#from setuptools import setup,find_packages

NAME = "certmaster"
VERSION = "0.24.9" 
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
	certmaster_cert_dir = "/var/lib/%s/%s" % (NAME,NAME)
	certmaster_cert_certs_dir = "/var/lib/%s/%s/certs" % (NAME, NAME)
	certmaster_cert_csrs_dir = "/var/lib/%s/%s/csrs" % (NAME, NAME)
	trigpath   = "/var/lib/%s/triggers/"% NAME
        pkipath    = "/etc/pki/%s" % NAME
        rotpath    = "/etc/logrotate.d"
        aclpath    = "%s/minion-acl.d" % etcpath
        setup(
                name="%s" % NAME,
                version = VERSION,
                author = "Lots",
                author_email = "func-list@redhat.com",
                url = "https://fedorahosted.org/certmaster/",
                license = "GPL",
		scripts = [
                     "scripts/certmaster", "scripts/certmaster-ca",
                     "scripts/certmaster-request", "scripts/certmaster-sync",
                ],
		# package_data = { '' : ['*.*'] },
                package_dir = {"%s" % NAME: "%s" % NAME
                },
		packages = ["%s" % NAME,
                ],
                data_files = [(initpath, ["init-scripts/certmaster"]),
                              (etcpath,  ["etc/minion.conf"]),
                              (etcpath,  ["etc/certmaster.conf"]),
                              (manpath,  ["docs/certmaster.1.gz"]),
                              (manpath,  ["docs/certmaster-request.1.gz"]),
                              (manpath,  ["docs/certmaster-ca.1.gz"]),
                              (manpath,  ["docs/certmaster-sync.1.gz"]),
			      (rotpath,  ['etc/certmaster_rotate']),
                              (logpath,  []),
			      (certdir,  []),
			      (certmaster_cert_dir, []),
			      (certmaster_cert_certs_dir, []),
			      (certmaster_cert_csrs_dir, []),
			      (etcpath,  []),
			      (pkipath,  []),
			      (aclpath,  []),
                              ("%s/peers"         % certdir,  []),
			      ("%s/sign/pre/"     % trigpath, []),
                              ("%s/sign/post/"    % trigpath, []),
                              ("%s/remove/pre/"   % trigpath, []),
                              ("%s/remove/post/"  % trigpath, []),
                              ("%s/request/pre/"  % trigpath, []),
                              ("%s/request/post/" % trigpath, []),
                ],
                description = SHORT_DESC,
                long_description = LONG_DESC
        )

