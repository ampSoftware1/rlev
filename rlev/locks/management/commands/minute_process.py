import logging
from django.core.management.base import BaseCommand
from locks.views import *

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

log_file_path = os.path.join(BASE_DIR, 'commands', 'minute_process.log')
logging.basicConfig(filename=log_file_path, level=logging.INFO)
class Command(BaseCommand):
    help = 'Run minute process'

    def handle(self, *args, **options):
        logging.info('------------------------------------------------------------')
        logging.info('minute process start at %s', datetime.now())
        
        do_passages()
        api = ApiRequest()

        lock_id = '16841228'

        print(api.update_lock_time(lock_id))


        logging.info('minute process end at %s', datetime.now())
        logging.info('------------------------------------------------------------')