# FIXME: more intelligent fault raises

"""
cert master listener

Copyright 2007, Red Hat, Inc
see AUTHORS

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

# standard modules
import SimpleXMLRPCServer
import string
import sys
import traceback
import os
import os.path
from OpenSSL import crypto

try:
    import hashlib
except ImportError:
    # Python-2.4.z ... gah! (or even 2.3!)
    import sha
    class hashlib:
        @staticmethod
        def new(algo):
            if algo == 'sha1':
                return sha.new()
            raise ValueError, "Bad checksum type"

import glob
import socket
import exceptions

import certs
import codes
import utils

import logger

from config import read_config
from commonconfig import CMConfig

CERTMASTER_LISTEN_PORT = 51235
CERTMASTER_CONFIG = "/etc/certmaster/certmaster.conf"

class CertMaster(object):
    def __init__(self, conf_file=CERTMASTER_CONFIG):
        self.cfg = read_config(conf_file, CMConfig)

        usename = utils.get_hostname(talk_to_certmaster=False)

        mycn = '%s-CA-KEY' % usename
        self.ca_key_file = '%s/certmaster.key' % self.cfg.cadir
        self.ca_cert_file = '%s/certmaster.crt' % self.cfg.cadir

        self.logger = logger.Logger().logger
        self.audit_logger = logger.AuditLogger()

        # if ca_key_file exists and ca_cert_file is missing == minion only setup
        if os.path.exists(self.ca_key_file) and not os.path.exists(self.ca_cert_file):
            return

        try:
            if not os.path.exists(self.cfg.cadir):
                os.makedirs(self.cfg.cadir)
            if not os.path.exists(self.ca_key_file) and not os.path.exists(self.ca_cert_file):
                certs.create_ca(CN=mycn, ca_key_file=self.ca_key_file, ca_cert_file=self.ca_cert_file, dnsname=usename)
        except (IOError, OSError), e:
            print 'Cannot make certmaster certificate authority keys/certs, aborting: %s' % e
            sys.exit(1)


        # open up the cakey and cacert so we have them available
        self.cakey = certs.retrieve_key_from_file(self.ca_key_file)
        self.cacert = certs.retrieve_cert_from_file(self.ca_cert_file)

        for dirpath in [self.cfg.cadir, self.cfg.certroot, self.cfg.csrroot]:
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)

        # setup handlers
        self.handlers = {
                 'wait_for_cert': self.wait_for_cert,
                 }


    def _dispatch(self, method, params):
        if method == 'trait_names' or method == '_getAttributeNames':
            return self.handlers.keys()


        if method in self.handlers.keys():
            return self.handlers[method](*params)
        else:
            self.logger.info("Unhandled method call for method: %s " % method)
            raise codes.InvalidMethodException

    def _sanitize_cn(self, commonname):
        commonname = commonname.replace('/', '')
        commonname = commonname.replace('\\', '')
        return commonname

    def wait_for_cert(self, csrbuf, with_triggers=True):
        """
           takes csr as a string
           returns True, caller_cert, ca_cert
           returns False, '', ''
        """

        try:
            csrreq = crypto.load_certificate_request(crypto.FILETYPE_PEM, csrbuf)
        except crypto.Error, e:
            #XXX need to raise a fault here and document it - but false is just as good
            return False, '', ''

        requesting_host = self._sanitize_cn(csrreq.get_subject().CN)

        if with_triggers:
            self._run_triggers(requesting_host, '/var/lib/certmaster/triggers/request/pre/*')

        self.logger.info("%s requested signing of cert %s" % (requesting_host,csrreq.get_subject().CN))
        # get rid of dodgy characters in the filename we're about to make

        certfile = '%s/%s.cert' % (self.cfg.certroot, requesting_host)
        csrfile = '%s/%s.csr' % (self.cfg.csrroot, requesting_host)

        # check for old csr on disk
        # if we have it - compare the two - if they are not the same - raise a fault
        self.logger.debug("csrfile: %s  certfile: %s" % (csrfile, certfile))

        if os.path.exists(csrfile):
            oldfo = open(csrfile)
            oldcsrbuf = oldfo.read()
            oldsha = hashlib.new('sha1')
            oldsha.update(oldcsrbuf)
            olddig = oldsha.hexdigest()
            newsha = hashlib.new('sha1')
            newsha.update(csrbuf)
            newdig = newsha.hexdigest()
            if not newdig == olddig:
                self.logger.info("A cert for %s already exists and does not match the requesting cert" % (requesting_host))
                # XXX raise a proper fault
            return False, '', ''


        # look for a cert:
        # if we have it, then return True, etc, etc
        if os.path.exists(certfile):
            slavecert = certs.retrieve_cert_from_file(certfile)
            cert_buf = crypto.dump_certificate(crypto.FILETYPE_PEM, slavecert)
            cacert_buf = crypto.dump_certificate(crypto.FILETYPE_PEM, self.cacert)
            if with_triggers:
                self._run_triggers(requesting_host,'/var/lib/certmaster/triggers/request/post/*')
            return True, cert_buf, cacert_buf

        # if we don't have a cert then:
        # if we're autosign then sign it, write out the cert and return True, etc, etc
        # else write out the csr

        if self.cfg.autosign:
            cert_fn = self.sign_this_csr(csrreq)
            cert = certs.retrieve_cert_from_file(cert_fn)
            cert_buf = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
            cacert_buf = crypto.dump_certificate(crypto.FILETYPE_PEM, self.cacert)
            self.logger.info("cert for %s was autosigned" % (requesting_host))
            if with_triggers:
                self._run_triggers(None,'/var/lib/certmaster/triggers/request/post/*')
            return True, cert_buf, cacert_buf

        else:
            # write the csr out to a file to be dealt with by the admin
            destfo = open(csrfile, 'w')
            destfo.write(crypto.dump_certificate_request(crypto.FILETYPE_PEM, csrreq))
            destfo.close()
            del destfo
            self.logger.info("cert for %s created and ready to be signed" % (requesting_host))
            if with_triggers:
                self._run_triggers(None,'/var/lib/certmaster/triggers/request/post/*')
            return False, '', ''

        return False, '', ''

    def get_csrs_waiting(self):
        hosts = []
        csrglob = '%s/*.csr' % self.cfg.csrroot
        csr_list = glob.glob(csrglob)
        for f in csr_list:
            hn = os.path.basename(f)
            hn = hn[:-4]
            hosts.append(hn)
        return hosts

    def remove_this_cert(self, hn, with_triggers=True):
        """ removes cert for hostname using unlink """
        cm = self
        csrglob = '%s/%s.csr' % (cm.cfg.csrroot, hn)
        csrs = glob.glob(csrglob)
        certglob = '%s/%s.cert' % (cm.cfg.certroot, hn)
        certs = glob.glob(certglob)
        if not csrs and not certs:
            # FIXME: should be an exception?
            print 'No match for %s to clean up' % hn
            return
        if with_triggers:
            self._run_triggers(hn,'/var/lib/certmaster/triggers/remove/pre/*')
        for fn in csrs + certs:
            print 'Cleaning out %s for host matching %s' % (fn, hn)
            self.logger.info('Cleaning out %s for host matching %s' % (fn, hn))
            os.unlink(fn)
        if with_triggers:
            self._run_triggers(hn,'/var/lib/certmaster/triggers/remove/post/*')

    def sign_this_csr(self, csr, with_triggers=True):
        """returns the path to the signed cert file"""
        csr_unlink_file = None

        if type(csr) is type(''):
            if csr.startswith('/') and os.path.exists(csr):  # we have a full path to the file
                csrfo = open(csr)
                csr_buf = csrfo.read()
                csr_unlink_file = csr

            elif os.path.exists('%s/%s' % (self.cfg.csrroot, csr)): # we have a partial path?
                csrfo = open('%s/%s' % (self.cfg.csrroot, csr))
                csr_buf = csrfo.read()
                csr_unlink_file = '%s/%s' % (self.cfg.csrroot, csr)

            # we have a string of some kind
            else:
                csr_buf = csr

            try:
                csrreq = crypto.load_certificate_request(crypto.FILETYPE_PEM, csr_buf)
            except crypto.Error, e:
                self.logger.info("Unable to sign %s: Bad CSR" % (csr))
                raise exceptions.Exception("Bad CSR: %s" % csr)

        else: # assume we got a bare csr req
            csrreq = csr


        requesting_host = self._sanitize_cn(csrreq.get_subject().CN)
        if with_triggers:
            self._run_triggers(requesting_host,'/var/lib/certmaster/triggers/sign/pre/*')


        certfile = '%s/%s.cert' % (self.cfg.certroot, requesting_host)
        self.logger.info("Signing for csr %s requested" % certfile)
        thiscert = certs.create_slave_certificate(csrreq, self.cakey, self.cacert, self.cfg.cadir)

        destfo = open(certfile, 'w')
        destfo.write(crypto.dump_certificate(crypto.FILETYPE_PEM, thiscert))
        destfo.close()
        del destfo


        self.logger.info("csr %s signed" % (certfile))
        if with_triggers:
            self._run_triggers(requesting_host,'/var/lib/certmaster/triggers/sign/post/*')


        if csr_unlink_file and os.path.exists(csr_unlink_file):
            os.unlink(csr_unlink_file)

        return certfile

    # return a list of already signed certs
    def get_signed_certs(self, hostglobs=None):
        certglob = "%s/*.cert" % (self.cfg.certroot)

        certs = []
        globs = "*"
        if hostglobs:
            globs = hostglobs

        for hostglob in globs:
            certglob = "%s/%s.cert" % (self.cfg.certroot, hostglob)
            certs = certs + glob.glob(certglob)

        signed_certs = []
        for cert in certs:
            # just want the hostname, so strip off path and ext
            signed_certs.append(os.path.basename(cert).split(".cert", 1)[0])

        return signed_certs

    def get_peer_certs(self):
        """
        Returns a list of all certs under peerroot
        """
        myglob = os.path.join(self.cfg.peerroot, '*.%s' % self.cfg.cert_extension)
        return glob.glob(myglob)

    # return a list of the cert hash string we use to identify systems
    def get_cert_hashes(self, hostglobs=None):
        certglob = "%s/*.cert" % (self.cfg.certroot)

        certfiles = []
        globs = "*"
        if hostglobs:
            globs = hostglobs

        for hostglob in globs:
            certglob = "%s/%s.cert" % (self.cfg.certroot, hostglob)
            certfiles = certfiles + glob.glob(certglob)

        cert_hashes = []
        for certfile in certfiles:
            cert = certs.retrieve_cert_from_file(certfile)
            cert_hashes.append("%s-%s" % (cert.get_subject().CN, cert.subject_name_hash()))

        return cert_hashes

    def _run_triggers(self, ref, globber):
        return utils.run_triggers(ref, globber)


class CertmasterXMLRPCServer(SimpleXMLRPCServer.SimpleXMLRPCServer):
    def __init__(self, addr):
        self.allow_reuse_address = True
        SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self, addr)


def serve(xmlrpcinstance):

    """
    Code for starting the XMLRPC service.
    """


    config = read_config(CERTMASTER_CONFIG, CMConfig)
    listen_addr = config.listen_addr
    listen_port = config.listen_port
    if listen_port == '':
        listen_port = CERTMASTER_LISTEN_PORT
    server = CertmasterXMLRPCServer((listen_addr,listen_port))
    server.logRequests = 0 # don't print stuff to console
    server.register_instance(xmlrpcinstance)
    xmlrpcinstance.logger.info("certmaster started")
    xmlrpcinstance.audit_logger.logger.info("certmaster started")
    server.serve_forever()

def excepthook(exctype, value, tracebackobj):
    exctype_blurb = "Exception occured: %s" % exctype
    excvalue_blurb = "Exception value: %s" % value
    exctb_blurb = "Exception Info:\n%s" % string.join(traceback.format_list(traceback.extract_tb(tracebackobj)))

    print exctype_blurb
    print excvalue_blurb
    print exctb_blurb

    log = logger.Logger().logger
    log.info(exctype_blurb)
    log.info(excvalue_blurb)
    log.info(exctb_blurb)


def main(argv):

    sys.excepthook = excepthook
    cm = CertMaster('/etc/certmaster/certmaster.conf')

    if "--version" in sys.argv or "-v" in sys.argv:
        print >> sys.stderr, file("/etc/certmaster/version").read().strip()
        sys.exit(0)

    if "daemon" in argv or "--daemon" in argv:
        utils.daemonize("/var/run/certmaster.pid")
    else:
        print "serving...\n"

    # just let exceptions bubble up for now
    serve(cm)


if __name__ == "__main__":
    #textdomain(I18N_DOMAIN)
    main(sys.argv)
