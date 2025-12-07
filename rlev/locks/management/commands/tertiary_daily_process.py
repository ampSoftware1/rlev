import logging
from django.core.management.base import BaseCommand
from locks.views import *

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

log_file_path = os.path.join(BASE_DIR, 'commands', 'tertiary_daily_process.log')
logging.basicConfig(filename=log_file_path, level=logging.INFO)
class Command(BaseCommand):
    help = 'Run Tertiary Daily process'

    def handle(self, *args, **options):
        logging.info('------------------------------------------------------------')
        logging.info('Tertiary Daily process start at %s', datetime.now())
        
        do_transmission('תהליך יומי', 'all')
        logging.info('Transmission completed')
        
        do_main_sync()
        logging.info('Main sync completed')
        
        do_import_locks_records()
        logging.info('Locks records import completed')

        logging.info('Tertiary Daily process end at %s', datetime.now())
        logging.info('------------------------------------------------------------')