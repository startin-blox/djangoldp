from django.contrib import admin
from guardian.admin import GuardedModelAdmin
from django.contrib.auth.admin import UserAdmin
from djangoldp.models import Activity, ScheduledActivity


class DjangoLDPAdmin(GuardedModelAdmin):
    '''
    An admin model representing a federated object. Inherits from GuardedModelAdmin to provide Django-Guardian
    object-level permissions
    '''
    pass


class DjangoLDPUserAdmin(UserAdmin, GuardedModelAdmin):
    '''An extension of UserAdmin providing the functionality of DjangoLDPAdmin'''

    list_display = ('urlid', 'email', 'first_name', 'last_name', 'date_joined', 'last_login', 'is_staff')

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        
        federated_fields = ['urlid', 'allow_create_backlink']
        if self.exclude is not None:
            federated_fields = list(set(federated_fields) - set(self.exclude))

        for fieldset in fieldsets:
            federated_fields = list(set(federated_fields) - set(fieldset[1]['fields']))

        if len(federated_fields) == 0:
            return fieldsets

        fieldsets = [('Federation', {'fields': federated_fields})] + list(fieldsets)

        return fieldsets


class ActivityAdmin(DjangoLDPAdmin):
    fields = ['urlid', 'type', 'local_id', 'external_id', 'created_at', 'success', 'payload_view', 'response_code',
              'response_location', 'response_body_view']
    list_display = ['created_at', 'type', 'local_id', 'external_id', 'success', 'response_code']
    readonly_fields = ['created_at', 'payload_view', 'response_location', 'response_code', 'response_body_view']

    def payload_view(self, obj):
        return str(obj.to_activitystream())

    def response_body_view(self, obj):
        return str(obj.response_to_json())


admin.site.register(Activity, ActivityAdmin)
admin.site.register(ScheduledActivity, ActivityAdmin)
