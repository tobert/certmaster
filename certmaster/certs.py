# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# Copyright (c) 2007 Red Hat, inc
#- Written by Seth Vidal skvidal @ fedoraproject.org

from OpenSSL import crypto
import socket
import os
import utils

def_country = 'UN'
def_state = 'FC'
def_local = 'Certmaster-town'
def_org = 'certmaster'
def_ou = 'slave-key'


def make_keypair(dest=None):
    pkey = crypto.PKey()
    pkey.generate_key(crypto.TYPE_RSA, 2048)
    if dest:
        destfd = os.open(dest, os.O_RDWR|os.O_CREAT, 0600)
        os.write(destfd, (crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey)))
        os.close(destfd)

    return pkey


def make_csr(pkey, dest=None, cn=None, hostname=None, emailaddr=None):
    req = crypto.X509Req()
    req.get_subject()
    subj  = req.get_subject()
    subj.C = def_country
    subj.ST = def_state
    subj.L = def_local
    subj.O = def_org
    subj.OU = def_ou
    if cn:
        subj.CN = cn
    elif hostname:
        subj.CN = hostname
    else:
        subj.CN = utils.gethostname()

    if emailaddr:
        subj.emailAddress = emailaddr
    else:
        subj.emailAddress = 'root@%s' % subj.CN

    req.set_pubkey(pkey)
    req.sign(pkey, 'md5')
    if dest:
        destfd = os.open(dest, os.O_RDWR|os.O_CREAT, 0644)
        os.write(destfd, crypto.dump_certificate_request(crypto.FILETYPE_PEM, req))
        os.close(destfd)

    return req


def retrieve_key_from_file(keyfile):
    fo = open(keyfile, 'r')
    buf = fo.read()
    keypair = crypto.load_privatekey(crypto.FILETYPE_PEM, buf)
    return keypair


def retrieve_csr_from_file(csrfile):
    fo = open(csrfile, 'r')
    buf = fo.read()
    csrreq = crypto.load_certificate_request(crypto.FILETYPE_PEM, buf)
    return csrreq


def retrieve_cert_from_file(certfile):
    fo = open(certfile, 'r')
    buf = fo.read()
    cert = crypto.load_certificate(crypto.FILETYPE_PEM, buf)
    return cert

def _build_extension_list(cert, dnsname=None, ca_enabled=False):
    subject = cert.get_subject()
    extensions = []

    if ca_enabled is True:
        extensions.append(crypto.X509Extension('basicConstraints', 1,'CA:TRUE'))
    else:
        extensions.append(crypto.X509Extension('basicConstraints', 1,'CA:FALSE'))

    if dnsname is None:
        dnsname = subject.CN

    # modeled after StoneVPN/app.py
    try:
        extensions.append(crypto.X509Extension('nsComment', 0, "Created by certmaster."))
        # set dnsName to commonName, which certmaster sets to the hostname
        extensions.append(crypto.X509Extension('subjectAltName', 0, "DNS:%s" % dnsname))
        # FIXME - add subjectkeyidentifier and authoritykeyidentifier extensions, too)
    except ValueError:
        print "Your version of pyOpenSSL does not support x509Extension properly. Try >= 0.9."

    return extensions

def create_ca(CN="Certmaster Certificate Authority", ca_key_file=None, ca_cert_file=None, dnsname=None):
    cakey = make_keypair(dest=ca_key_file)
    careq = make_csr(cakey, cn=CN)
    cacert = crypto.X509()
    cacert.set_serial_number(0)
    cacert.gmtime_adj_notBefore(0)
    cacert.gmtime_adj_notAfter(60*60*24*365*10) # 10 yrs - hard to beat this kind of cert!
    cacert.set_issuer(careq.get_subject())
    cacert.set_subject(careq.get_subject())
    cacert.set_pubkey(careq.get_pubkey())
    cacert.set_version(2)
    cacert.add_extensions(_build_extension_list(cert=cacert, dnsname=dnsname, ca_enabled=True))
    cacert.sign(cakey, 'sha1')
    if ca_cert_file:
        destfo = open(ca_cert_file, 'w')
        destfo.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cacert))
        destfo.close()

def _get_serial_number(cadir):
    serial = '%s/serial.txt' % cadir
    i = 1
    if os.path.exists(serial):
        f = open(serial, 'r').read()
        f = f.replace('\n','')
        try:
            i = int(f)
            i+=1
        except ValueError, e:
            i = 1

    _set_serial_number(cadir, i)
    return i


def _set_serial_number(cadir, last):
    serial = '%s/serial.txt' % cadir
    f = open(serial, 'w')
    f.write(str(last) + '\n')
    f.close()

def create_slave_certificate(csr, cakey, cacert, cadir, slave_cert_file=None):
    cert = crypto.X509()
    cert.set_serial_number(_get_serial_number(cadir))
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(60*60*24*365*10) # 10 yrs - hard to beat this kind of cert!
    cert.set_issuer(cacert.get_subject())
    cert.set_subject(csr.get_subject())
    cert.set_pubkey(csr.get_pubkey())
    cert.set_version(2)
    cert.add_extensions(_build_extension_list(cert=cert))
    cert.sign(cakey, 'sha1')
    if slave_cert_file:
        destfo = open(slave_cert_file, 'w')
        destfo.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        destfo.close()
    return cert

def check_cert_key_match(cert, key):
    if not isinstance(cert, crypto.X509Type):
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert)
    if not isinstance(key, crypto.PKeyType):
        key = crypto.load_privatekey(crypto.FILETYPE_PEM, key)

    from OpenSSL import SSL
    context = SSL.Context(SSL.SSLv3_METHOD)
    try:
        context.use_certificate(cert)
        context.use_privatekey(key)
        return True
    except:
        return False
