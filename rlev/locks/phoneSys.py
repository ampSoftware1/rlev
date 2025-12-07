from locks.models import *

def total_minutes_of_day():
    now = datetime.datetime.now()
    total_minutes = now.minute + now.hour * 60
    return total_minutes


def unlock_by_phone_menu(phone_data):
    phone = phone_data['ApiPhone']

    phone_exists = Phone.objects.filter(phone=phone).exists()
    if not phone_exists:
        return phone_sys_message('אין הרשאות פעילות למספר טלפון זה', 'hangup')

    phone_object = Phone.objects.get(phone=phone)
    permissions = Permission.objects.filter(type_object_id=16, object_id=phone_object.id)

    if not permissions:
        return phone_sys_message('אין הרשאות פעילות למספר טלפון זה', 'hangup')
    
    if permissions.count() == 1:
        permission = permissions.first()
    else: 
        if not "lock_index" in phone_data:
            voice = "בחר את המנעול הרצוי לפתיחה ולאחריו הקש סולמית, "
            keys = ""
            for index, permission in enumerate(permissions):
                voice += "עבור מנעול " + permission.lock.lock_alias
                voice += " הקש " + str(index + 1) + ', '

            return phone_sys_read(voice, 'lock_index')
        else:
            lock_index = int(phone_data['lock_index'])
            if lock_index > permissions.count():
                return phone_sys_message('ההקשה אינה תקינה', '/' + phone_data['ApiExtension'])
            permission = permissions[lock_index - 1]
        
    permision_is_valid = False
    lock_id = permission.lock.id
    if permission.type_permission == 1:   
        permision_is_valid = True        
    elif permission.type_permission == 2:
        if permission.start_date <= time.time() * 1000 and permission.end_date >= time.time() * 1000:
            permision_is_valid = True
    elif permission.type_permission == 3:
        if permission.start_date <= time.time() * 1000 and permission.end_date >= time.time() * 1000:
            cycle_config = permission.cyclic_config

            for cycle in cycle_config:
                minutes = total_minutes_of_day()
                day_of_week = datetime.today().weekday()
                day_of_week = (day_of_week + 1) % 7
                if day_of_week == 0:
                    day_of_week = 7
                
                if cycle['weekDay'] == day_of_week and cycle['startTime'] <= minutes and cycle['endTime'] >= minutes:
                    permision_is_valid = True
                    break


    if permision_is_valid:
        unlock = unlock_by_phone(lock_id, phone_object.id)
        if unlock:
            return phone_sys_message('המנעול נפתח בהצלחה', 'hangup')
        else:
            return phone_sys_message('ארעה שגיאה בפתיחת המנעול', 'hangup')
    else:
        return phone_sys_message('ההרשאה לפתיחת המנעול אינה בתוקף', 'hangup')


def unlock_by_phone(lock_id, phone_id):
    lock = Lock.objects.get(id=lock_id)
    lock_id_ttl = lock.lock_id_ttl

    phone = Phone.objects.get(id=phone_id)

    api = ApiRequest()
    response = api.unlock(lock_id_ttl)
    if response:
        unlock_data = dict(
            success=1,
            lock_id=lock_id,
            record_id=time.time() * 1000,
            type_object_id=16, 
            person_id=phone.person.id,
            person_name=phone.person.get_name(),
            done_by=phone.phone,
            object_record_description=phone.person.get_name() + " (" + phone.get_description() + ")",
            record_type=99,
            lock_date=time.time() * 1000,
            server_date=time.time() * 1000,
            record_type_from_lock=0,
        )
        LockRecord(**unlock_data).save()
        return True
    else:
        return False








def phone_sys_message(message, go_to):
    return 'id_list_message=t-' + message + '&go_to_folder=' + go_to

def phone_sys_read(voice, param):
    return 'read=t-' + voice + '=' + param + ',,,,,No'

