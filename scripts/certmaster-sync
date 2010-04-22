#!/usr/bin/python -tt

# Syncs the valid CA-signed certificates from certmaster to all known
# hosts via func.  To be called during the post-sign hook to copy new
# certificates and from the post-clean hook in order to purge stale
# certificates.  Requires 'sync_certs' to be set in certmaster.conf.

import os
import sys
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


import xmlrpclib
from glob import glob
from time import sleep
from certmaster import certmaster as certmaster
from func.overlord.client import Client
from func.CommonErrors import Func_Client_Exception
import func.jobthing as jobthing

def syncable(cert_list):
    """
    Calls out to known hosts to find out who is configured for
    peering.  Returns a list of hostnames who support peering.
    """
    try:
        fc = Client('*', async=True, nforks=len(cert_list))
    except Func_Client_Exception:
        # we are either:
        #   - signing the first minion
        #   - cleaning the only minion
        # so there's nothing to hit.  This shouldn't happen
        # when we get called from the 'post-fetch' trigger
        # (future work)
        return None

    # Only wait for a few seconds.  Assume anything that doesn't get
    # back by then is a lost cause.  Don't want this trigger to spin
    # too long.
    ticks = 0
    return_code = jobthing.JOB_ID_RUNNING
    results = None
    job_id = fc.certmastermod.peering_enabled()
    while return_code != jobthing.JOB_ID_FINISHED and ticks < 3:
        sleep(1)
        (return_code, results) = fc.job_status(job_id)
        ticks += 1

    hosts = []
    for host, result in results.iteritems():
        if result == True:
            hosts.append(host)
    return hosts

def remote_peers(hosts):
    """
    Calls out to hosts to collect peer information
    """
    fc = Client(';'.join(hosts))
    return fc.certmastermod.known_peers()

def local_certs():
    """
    Returns (hostname, sha1) hash of local certs
    """
    globby = '*.%s' % cm.cfg.cert_extension
    globby = os.path.join(cm.cfg.certroot, globby)
    files = glob(globby)
    results = []
    for f in files:
        hostname = os.path.basename(f).replace('.' + cm.cfg.cert_extension, '')
        digest = checksum(f)
        results.append([hostname, digest])
    return results

def checksum(f):
    thissum = hashlib.new('sha1')
    if os.path.exists(f):
        fo = open(f, 'r')
        data = fo.read()
        fo.close()
        thissum.update(data)

    return thissum.hexdigest()

def remove_stale_certs(local, remote):
    """
    For each cert on each remote host, make sure it exists locally.
    If not then it has been cleaned locally and needs unlinked
    remotely.
    """
    local = [foo[0] for foo in local] # don't care about checksums
    for host, peers in remote.iteritems():
        fc = Client(host)
        die = []
        for peer in peers:
            if peer[0] not in local:
                die.append(peer[0])
        if die != []:
            fc.certmastermod.remove_peer_certs(die)

def copy_updated_certs(local, remote):
    """
    For each local cert, make sure it exists on the remote with the
    correct hash.  If not, copy it over!
    """
    for host, peers in remote.iteritems():
        fc = Client(host)
        for cert in local:
            if cert not in peers:
                cert_name = '%s.%s' % (cert[0], cm.cfg.cert_extension)
                full_path = os.path.join(cm.cfg.certroot, cert_name)
                fd = open(full_path)
                certblob = fd.read()
                fd.close()
                fc.certmastermod.copy_peer_cert(cert[0], xmlrpclib.Binary(certblob))

def main():
    forced = False
    try:
        if sys.argv[1] in ['-f', '--force']:
            forced = True
    except IndexError:
        pass

    if not cm.cfg.sync_certs and not forced:
        sys.exit(0)

    certs = glob(os.path.join(cm.cfg.certroot,
                              '*.%s' % cm.cfg.cert_extension))
    hosts = syncable(certs)
    if not hosts:
        return 0
    remote = remote_peers(hosts)
    local = local_certs()
    remove_stale_certs(local, remote)
    copy_updated_certs(local, remote)

if __name__ == "__main__":
    cm = certmaster.CertMaster()
    main()
