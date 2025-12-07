import logging
from django.core.management.base import BaseCommand
from locks.views import *

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

log_file_path = os.path.join(BASE_DIR, 'commands', 'daily_process.log')
logging.basicConfig(filename=log_file_path, level=logging.INFO)
class Command(BaseCommand):
    help = 'Run daily process'

    def handle(self, *args, **options):
        logging.info('------------------------------------------------------------')
        logging.info('Daily process start at %s', datetime.now())
        
        check_locks_battery()

        logging.info('Daily process end at %s', datetime.now())
        logging.info('------------------------------------------------------------')