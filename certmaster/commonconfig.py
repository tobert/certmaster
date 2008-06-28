"""
Default configuration values for certmaster items when
not specified in config file.

Copyright 2008, Red Hat, Inc
see AUTHORS

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""


from config import BaseConfig, BoolOption, IntOption, Option

class CMConfig(BaseConfig):
    log_level = Option('INFO')
    listen_addr = Option('')
    cadir = Option('/etc/pki/certmaster/ca')
    cert_dir = Option('/etc/pki/certmaster')
    certroot =  Option('/var/lib/certmaster/certmaster/certs')
    csrroot = Option('/var/lib/certmaster/certmaster/csrs')
    cert_extension = Option('cert')
    autosign = BoolOption(False)

class MinionConfig(BaseConfig):
    log_level = Option('INFO')
    certmaster = Option('certmaster')
    cert_dir = Option('/etc/pki/certmaster')

