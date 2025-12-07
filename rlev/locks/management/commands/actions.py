from locks.models import *
from django.core.management.base import BaseCommand
import requests

from datetime import datetime, timedelta
class Command(BaseCommand):

    def handle(self, *args, **options):

        import requests

        url = "https://my.nayax.com/core/Public/facade.aspx?model=operations/cards&action=Card.Cards_Update&&card_type_lut_id=33&changed_actor=true&excelImport=false"
        headers = {
            "X-Nayax-Validation-Token": "2FB5IZu/mInXF9b0eTWicRMcBTl90HCP0ES1Q/IqVKDdGVcpY/2ApW1AuNR4ID5KcmT4lo/oGFQXSUHvIY8GpkPzHhcNJjHwumofivTu17w=",  # Add more headers if needed
        }

        cookies = {
            "language_id": "4",
            "__cflb": "02DiuJHeEFyZ3Y87yMafDtz4R9PN88Tp4aur5jc8tHxRA",
            "_RVC": "2diQRLgXd8FZYbUpn9lzjuOKp0p%2Ba8btqAT%2BRioo2gtKxF%2FYpCwV%2BubFs%2FBNzIff",
            "_ga_YQ9SLQXLM1": "GS1.1.1724701367.9.0.1724702454.0.0.0",
            "OptanonConsent": "isGpcEnabled=0&datestamp=Mon+Aug+26+2024+23%3A01%3A20+GMT%2B0300+(%D7%A9%D7%A2%D7%95%D7%9F+%D7%99%D7%A9%D7%A8%D7%90%D7%9C+(%D7%A7%D7%99%D7%A5))&version=202405.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&",
            "consentId": "dc620f78-231d-4ed1-9f03-e5fb9ddb0a89&interactionCount=2&isAnonUser=1&landingPath=NotLandingPage&groups=C0003%3A1%2CC0004%3A1%2CC0001%3A1%2CC0002%3A1&AwaitingReconsent=false&intType=1&geolocation=IL%3BJM",
            ".AspNetCore.Antiforgery.PZ9UDq_NBM0": "CfDJ8LmD4TjzHQFAppIFLJjRux2wBKgJ8O0cFJNaMegbgpw6iyqvzsXl_V_l6U6wnZG_unKtvxRdlG2gXUK88JefkNwknH46-f6Ym52M5xKPCMqOui8Pzyx7CQW5mh4p1cWvQnB2ez5puOvS5AhM3G3-FNg",
            "_ga": "GA1.1.539220048.1722378102",
            "nxauth": "CfDJ8LmD4TjzHQFAppIFLJjRux1XZZhL6shBm2dc52QkdUHuVDkFs5Dr33hRymZ11JYzFO1ZsrEKccNBIfC3MRVcQZDyyo1p5TUtFR-9vF8IxBW2m4zHo4wQdqSHEl2Pu-YisSh7xeumRl9IkjCEKmkpOPRLRaDObA2px2-_itWx9L3RyTxZfkf9h43DjghBqEQ_tfb6hbxc7zRnRBP53ZUmgMacAvya-70NdcDxsMg4vAKbo3lDcTOkI3LpbFILMT4bwXCVSYUmVjQ9ZkBgQPcJJNASejttEDJlwe30UH_3pa8CCffeHSoIC9gUwQZ3aZnDTqcsCIGqKdA6fQI3RiGjXrE",
            "OptanonAlertBoxClosed": "2024-07-30T22:25:08.439Z",
            "_ga_ZDHBT72N5H": "GS1.1.1724701362.8.1.1724702489.25.0.0",
            "sPersist": "%3Croot%3E%3Cuser_data%20card_type%3D%2233%22%20status_id%3D%221%22%2F%3E%3C%2Froot%3E"
        }

        data = """
                    <?xml version="1.0" encoding="utf-8"?><metadata result="SUCCESS">
                    <root><MonyxCard action="new" month_issue="8" month_issue_dirty="1" month_issue_original="" month_active="8" month_active_dirty="1" month_active_original="" month_expiration="8" month_expiration_dirty="1" month_expiration_original="" static_sector="" dynamic_sector1="" dynamic_sector2=""/><row action="new" actor_description="arieariearie" actor_description_dirty="1" actor_description_original="" actor_id="2000441926" actor_id_dirty="1" actor_id_original="" actor_type_id="5" actor_type_id_dirty="1" actor_type_id_original="" card_type_lut_id="33" card_type_lut_id_dirty="1" card_type_lut_id_original="" card_physical_type_lut_id="30000531" card_physical_type_lut_id_dirty="1" card_physical_type_lut_id_original="" card_number="115858" card_number_dirty="1" card_number_original="" display_card_string="1" display_card_string_dirty="1" display_card_string_original="" status_id="1" status_id_dirty="1" status_id_original="" card_holder_name="test" card_holder_name_dirty="1" card_holder_name_original="" card_user_identity_id="" email="" note=""/><PrepaidCard action="new" use_wd_limit="0" daily_credit_money="6" daily_credit_money_dirty="1" daily_credit_money_original="" monthly_credit_money="60" monthly_credit_money_dirty="1" monthly_credit_money_original="" is_money="1" is_money_dirty="1" is_money_original="" is_accumulated="0" is_accumulated_dirty="1" is_accumulated_original="" is_single_use="0" is_single_use_dirty="1" is_single_use_original="" is_revalue_card="0" is_revalue_card_dirty="1" is_revalue_card_original="" is_revalue_credit_card="0" is_revalue_credit_card_dirty="1" is_revalue_credit_card_original="" daily_usage="" weekly_usage="" monthly_usage="" total_usage="" monthly_reload_credit_money="1" monthly_reload_credit_money_dirty="1" monthly_reload_credit_money_original=""/></root><CardGroups actor_description="ariedariedaried&quot;a" machine_group_descr="ddddd" group_id="1684" checked="0" daily_limit="3" daily_limit_dirty="1" daily_limit_original="" action="update"/><CardGroups actor_description="ariedariedaried&quot;a" machine_group_descr="fff" group_id="1710" checked="0"/><CardGroups actor_description="ariedariedaried&quot;a" machine_group_descr="ariecariecariec" group_id="1711" checked="0" ui_selected="1" daily_limit="3" daily_limit_dirty="1" daily_limit_original="" action="update"/><CardGroups actor_description="ariedariedaried&quot;a" machine_group_descr="ff" group_id="2670" checked="0"/><CardGroups actor_description="ariedariedaried&quot;a" machine_group_descr="aaa" group_id="9646" checked="0"/><CardGroups actor_description="ariedariedaried&quot;a" machine_group_descr="aaa" group_id="490305" checked="0"/><CardGroups actor_description="ariedariedaried&quot;a" machine_group_descr="ariemariemaried" group_id="905636161" checked="0"/><CardGroups actor_description="ariedariedaried&quot;a" machine_group_descr="snacks" group_id="946537408" checked="0"/></metadata>
            """

        response = requests.post(url, headers=headers, cookies=cookies, data=data)

        print(response.status_code)
        print(response.text)
