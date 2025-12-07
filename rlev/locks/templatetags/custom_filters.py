from django import template
from django.utils.safestring import mark_safe
import datetime
import pytz

register = template.Library()


@register.filter
def battery_status(value):
    if value >= 75:
        return mark_safe('<i class="bi bi-battery-full"></i> ' + str(value) + '%')
    elif value >= 25:
        return mark_safe('<i class="bi bi-battery-half"></i> ' + str(value) + '%')
    else:
        return mark_safe('<span class="text-danger"> <i class="bi bi-battery"></i> ' + str(value) + '%' + '</span>')


@register.filter
def gateway_status(value):
    if value == 1:
        return mark_safe('<i class="bi bi-wifi"></i> מחובר' )
    else:
       return mark_safe('<i class="bi bi-wifi-off"></i> מנותק')

def time_utc_to_local(time):
    dt_object_utc = datetime.datetime.utcfromtimestamp(time)
    server_timezone = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
    dt_object_local = dt_object_utc.replace(tzinfo=pytz.utc).astimezone(server_timezone)
    return dt_object_local

@register.filter
def time_to_datetime(value):
    if not value:
        return '-'
    value /= 1000 

    dt_object_local = time_utc_to_local(value)
    formatted_date = dt_object_local.strftime('%d/%m/%Y %H:%M:%S')
    return formatted_date


@register.filter
def time_to_time(value):
    value = value /1000
    dt_object_local = time_utc_to_local(value)
    formatted_date = dt_object_local.strftime('%H:%M:%S')
    return formatted_date


@register.filter
def time_to_date(value, with_time=False):
    if not value:
        return 0
    value = value / 1000
    dt_object_local = time_utc_to_local(value)
    if with_time:
        formatted_date = dt_object_local.strftime('%Y-%m-%d %H:%M:%S')
    else:
        formatted_date = dt_object_local.strftime('%Y-%m-%d')
    return formatted_date

@register.filter
def dict_get(d, key):
    return d.get(key, '')