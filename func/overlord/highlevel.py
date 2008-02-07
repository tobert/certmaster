##
## func higher level API interface for overlord side operations
##
## Copyright 2007, Red Hat, Inc
## Michael DeHaan <mdehaan@redhat.com>
## +AUTHORS
##
## This software may be freely redistributed under the terms of the GNU
## general public license.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
##

import exceptions

class HigherLevelObject:

   def __init__(self, client):
       self.client = client_handle

   def modify(self, key, properties):
       """
       Modify or create an entity named key.  
       properties should contain all neccessary fields.
       """
       raise exceptions.NotImplementedError

   def remove(self, key):
       """
       Remove an entity named key.
       """
       raise exceptions.NotImplementedError

   def list(self):
       """
       List all objects
       """
       raise exceptions.NotImplementedError  
