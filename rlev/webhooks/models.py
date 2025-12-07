from django.db import models

def get_unique_id():
    import uuid
    return str(uuid.uuid4())

    
class CrossData(models.Model):
    data_from_sf = models.JSONField()
    data_from_page = models.JSONField()
    fields = models.JSONField()
    uuid = models.CharField(max_length=255, unique=True, default=get_unique_id)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_cross_prioritys(self):
        cross_prioritys = {
            'cross_priority_1': 0,
            'cross_priority_2': 0,
            'cross_priority_3': 0
        }
        data_from_sf = self.data_from_sf
        data_from_page = self.data_from_page
        for field in self.fields:
            priority = field['priority']
            field_name = field['field_name']

            for data in data_from_sf:
                if data[field_name] and data[field_name] != data_from_page[field_name]:
                    cross_prioritys[f'cross_priority_{priority}'] += 1
            

        return cross_prioritys
