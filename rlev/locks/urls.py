import os
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import consumers
from .views import *


urlpatterns = [
    path('', dashboard, name='dashboard'),
    
    path('locks', locks),
    path('lock/<int:lock_id>', lock),
    path('check_lock_status/<int:lock_id>', check_lock_status),
    path('change_lock_status/<int:lock_id>/<str:current_status>', change_lock_status),
    path('change_lock_alias/<int:lock_id>/<str:new_alias>', change_lock_alias),
    path('add_lock', add_lock),
    path('delete_lock/<int:lock_id>', delete_lock),
    path('save_lock/<int:lock_id_ttl>', save_lock),
    path('check_lock/<int:lock_id_ttl>', check_lock),

    path('get_lock_child_list/<str:type_child>/<int:lock_id>', get_lock_child_list),
    path('get_child_locks/<str:child_name>/<int:child_id>', get_child_locks),
    path('add_or_remove_locks_to_child', add_or_remove_locks_to_child),

    path('get_lock_link_list/<str:type_link>/<int:lock_id>', get_lock_link_list),
    path('get_lock_link_options/<str:type_link>/<int:lock_id>', get_lock_link_options),
    path('add_link_to_lock/<str:type_link>/<int:lock_id>/<int:object_id>', add_link_to_lock),
    path('remove_link_from_lock/<str:type_link>/<int:object_id>', remove_link_from_lock),
    path('delete_lock_child/<str:type_child>/<int:object_id>', delete_lock_child),
    path('select_locks', select_locks),

    path('passages', passages),
    path('passage', passage),
    path('passage/<int:passage_id>', passage),
    path('get_passages_list', get_passages_list),
    path('get_locks_passage_list/<int:passage_id>', get_locks_passage_list),
    path('save_passage', save_passage),
    path('delete_passage/<int:passage_id>', delete_passage),
    path('change_active_passage/<int:passage_id>/<int:value>', change_active_passage),
    path('add_locks_passage/<int:passage_id>', add_locks_passage),
    path('lock_passage_action/<str:action>/<int:lock_passage_id>', lock_passage_action),
    path('do_passage_locks_actions/<int:passage_id>', do_passage_locks_actions),

    path('get_passage_users/<int:passage_id>', get_passage_users),
    path('remove_user_from_passage/<int:user_id>', remove_user_from_passage),
    path('get_user_passage_options/<int:passage_id>', get_user_passage_options),
    path('add_user_to_passage/<int:passage_id>/<int:user_id>', add_user_to_passage),

    path('houses', houses),
    path('houses_reports', houses_reports),
    path('get_houses_report/<str:type_get>/<str:value>',get_houses_report ),
    path('update_houses_report/<int:report_id>',update_houses_report ),
    path('delete_houses_report/<int:report_id>', delete_houses_report),
    path('get_houses_report_pdf', get_houses_report_pdf),

    path('get_hostings_houses_for_date/<str:date>', get_hostings_houses_for_date),

    path('select_houses', select_houses),

    path('house', house),
    path('house/<int:house_id>', house),
    path('add_locks_to_house/<int:house_id>', add_locks_to_house),
    # path('get_locks_house_list/<int:house_id>', get_locks_house_list),
    path('get_house_link_list/<str:type_link>/<int:house_id>', get_house_link_list),
    path('get_house_link_options/<str:type_link>/<int:house_id>', get_house_link_options),
    path('add_link_to_house/<str:type_link>/<int:house_id>/<int:object_id>', add_link_to_house),
    path('remove_link_from_house/<str:type_link>/<int:object_id>', remove_link_from_house),
    # path('remove_lock_from_house/<int:lock_house_id>', remove_lock_from_house),
    path('get_house_child_list/<str:type_child>/<int:house_id>', get_house_child_list),
    path('save_house', save_house),
    path('delete_house/<int:house_id>', delete_house),
    path('get_houses_with_hosting_status', get_houses_with_hosting_status),
    path('houses_users_permissions', houses_users_permissions),
    path('get_houses_users_permissions/<int:user_id>', get_houses_users_permissions),
    path('remove_house_from_user/<int:user_id>/<int:house_id>', remove_house_from_user),
    path('add_houses_to_user', add_houses_to_user),

    path('hostings', hostings),
    path('hosting', hosting),
    path('hosting/<int:hosting_id>', hosting),
    path('doplicate_hosting/<int:hosting_id>', doplicate_hosting),
    path('save_hosting', save_hosting),
    path('delete_hosting/<int:hosting_id>', delete_hosting),

    path('get_hosting_record/<str:guest_id_number>', get_hosting_record),
    path('get_details_of_guest/<str:guest_id_number>', get_details_of_guest),
    path('get_hosting_options', get_hosting_options),

    path('permissions', permissions),
    path('permission/<int:permission_id>', permission),
    path('add_permissions', add_permissions),
    path('save_permissions', save_permissions),
    path('remove_permissions', remove_permissions),
    
    path('main_sync', main_sync),
    path('sync/<int:lock_id>', sync),
    path('transmission', transmission),
    path('resend_transmission/<int:transmission_id>', resend_transmission),
    path('delete_transmission/<int:transmission_id>', delete_transmission),
    path('resend_all_transmissions', resend_all_transmissions),
    path('transmission_all', transmission_all),
    path('get_amount_in_transmission', get_amount_in_transmission),

    path('cards', cards),
    path('get_cards_list', get_cards_list),
    path('get_cards_list/<int:person_id>', get_cards_list),
    path('delete_cards', delete_cards),
    path('card/<int:card_id>', card),
    path('add_card/<int:person_id>', add_card),
    path('save_card', save_card),
    path('change_coffee_card_status/<int:card_id>/<int:status>', change_coffee_card_status),

    path('childs_locks/<str:child_name>', childs_locks),

    path('access_group', access_group),
    path('add_access_group/<str:group_name>', add_access_group),
    path('delete_group/<int:group_id>', delete_group),

    path('persons', persons),
    path('persons_list',persons_list),
    path('hostings_ichilov', hostings_ichilov),
    path('add_person', add_person),
    path('merge_person/<int:source_person_id>', merge_person),
    path('do_merge_person/<int:source_person_id>/<int:target_person_id>', do_merge_person),
    path('person', person),
    path('person/<int:person_id>', person),
    path('get_person_permission_objects/<int:person_id>',get_person_permission_objects),
    path('get_person_child_list/<str:type_child>/<int:person_id>', get_person_child_list),
    path('delete_person_child/<str:type_child>/<int:object_id>', delete_person_child),
    path('save_person', save_person),
    path('delete_person/<int:person_id>', delete_person),
    path('get_role_options', get_role_options),
    path('check_id_number/<str:id_number>', check_id_number),
    path('upload_person_id_file', upload_person_id_file),
    path('delete_person_id_file', delete_person_id_file),

    path('records', records),

    path('phone/<int:phone_id>', phone),
    path('save_phone', save_phone),
    path('add_phone/<int:person_id>', add_phone),

    path('transmissions', transmissions),
    path('get_transmissions_list', get_transmissions_list),

    path('users', users),
    path('add_user', add_user),
    path('user/<int:user_id>', user),
    path('save_user', save_user),
    path('delete_user/<int:user_id>', delete_user),

    path('import_locks_records', import_locks_records),
    path('get_excel_cards', get_excel_cards),
    path('get_excel_hostings_summary', get_excel_hostings_summary),
    path('get_excel_hostings_daily', get_excel_hostings_daily),

    path('unlock_by_phone', view_unlock_by_phone),
    path('send_feedback/<str:type_hosting>/<int:hosting_id>', send_feedback),
    path('test', test),
    path('upload_file', upload_file)
    
] + static('/media/', document_root=os.path.join(settings.BASE_DIR, 'media'))

