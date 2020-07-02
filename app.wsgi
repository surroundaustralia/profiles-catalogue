import sys
import logging
sys.path.insert(0, '/var/www/profiles-catalogue')
sys.path.insert(0, '/var/www/profiles-catalogue/profcat')
logging.basicConfig(stream=sys.stderr)

from app import app as application
