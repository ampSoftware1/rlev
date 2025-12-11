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

        logging.info('Starting database backup...')

        bkup_database()




def bkup_database():
    import requests
    import subprocess
    from django.conf import settings
    
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(BASE_DIR, 'backups', f'db_backup_{timestamp}.sql')
        os.makedirs(os.path.dirname(backup_file), exist_ok=True)
        
        # Get database settings from Django
        db_settings = settings.DATABASES['default']
        db_name = db_settings['NAME']
        db_user = db_settings['USER']
        db_password = db_settings['PASSWORD']
        db_host = db_settings.get('HOST', 'localhost')
        
        # MySQL dump command
        mysqldump_cmd = f'mysqldump -u {db_user} -p{db_password} -h {db_host} {db_name} > {backup_file}'
        result = subprocess.run(mysqldump_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error('MySQL dump failed: %s', result.stderr)
            return
        
        logging.info('Database backup completed: %s', backup_file)
        
        # Send backup file via webhook
        webhook_url = "https://hook.eu1.make.com/p1kso9x2p2ht6ykip1cvahqw7wwyzmyq"
        
        with open(backup_file, 'rb') as f:
            files = {
                'backup_file': (
                    f'db_backup_{timestamp}.sql',
                    f.read(),
                    'application/sql'
                )
            }
            
            data = {
                'type': 'bkup',
                'timestamp': timestamp,
                'database': db_name
            }
            
            response = requests.post(webhook_url, data=data, files=files, timeout=30)
            response.raise_for_status()
            logging.info('Backup file sent to webhook successfully')
            
    except Exception as e:
        logging.error('Database backup failed: %s', str(e))