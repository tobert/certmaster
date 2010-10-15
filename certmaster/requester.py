"""
certmaster requester -- asks for certs
any python app that wants to use certmaster can use this module

Copyright 2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import utils

def request_cert(hostname=None):
    # this should be enough, but do we want to allow parameters
    # for overriding the server and port from the config file?
    # maybe not. -- mpd
    utils.create_minion_keys(hostname)
