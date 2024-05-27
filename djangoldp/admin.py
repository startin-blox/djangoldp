from csv import DictWriter
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import FieldDoesNotExist
from django.http import HttpResponse
from guardian.admin import GuardedModelAdmin
from djangoldp.models import Activity, ScheduledActivity, Follower
from djangoldp.activities.services import ActivityQueueService


class DjangoLDPAdmin(GuardedModelAdmin):
    '''
    An admin model representing a federated object. Inherits from GuardedModelAdmin to provide Django-Guardian
    object-level permissions
    '''
    actions = ['export_csv']
    export_fields = []

    def resolve_verbose_name(self, field_path):
        field = self
        for field_name in field_path.split('__'):
            try:
                field = field.model._meta.get_field(field_name)
            except FieldDoesNotExist:
                return None
        return field.verbose_name

    @admin.action(description="Export CSV")
    def export_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response['Content-Disposition'] = f'attachment; filename="{self.model.__name__}.csv"'
        # only keep fields that can be resolved, keep only urlid if none
        field_list = list(filter(self.resolve_verbose_name, self.export_fields or self.list_display)) or ['urlid']
        headers = {field:self.resolve_verbose_name(field) for field in field_list}

        writer = DictWriter(response, fieldnames=field_list)
        writer.writerow(headers)
        writer.writerows(queryset.values(*field_list))
        return response


class DjangoLDPUserAdmin(UserAdmin, DjangoLDPAdmin):
    '''An extension of UserAdmin providing the functionality of DjangoLDPAdmin'''

    list_display = ('urlid', 'email', 'first_name', 'last_name', 'date_joined', 'last_login', 'is_staff')
    search_fields = ['urlid', 'email', 'first_name', 'last_name']
    ordering = ['urlid']

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


@admin.action(description='Resend activity')
def resend_activity(modeladmin, request, queryset):
    for a in queryset:
        ActivityQueueService.send_activity(a.external_id, a.to_activitystream())
resend_activity.short_description = 'Resend activity'


@admin.register(Activity, ScheduledActivity)
class ActivityAdmin(DjangoLDPAdmin):
    fields = ['urlid', 'type', 'local_id', 'external_id', 'created_at', 'success', 'payload_view', 'response_code',
              'response_location', 'response_body_view']
    list_display = ['created_at', 'type', 'local_id', 'external_id', 'success', 'response_code']
    readonly_fields = ['created_at', 'payload_view', 'response_location', 'response_code', 'response_body_view']
    search_fields = ['urlid', 'type', 'local_id', 'external_id', 'response_code']
    actions = [resend_activity]

    def payload_view(self, obj):
        return str(obj.to_activitystream())

    def response_body_view(self, obj):
        return str(obj.response_to_json())


@admin.register(Follower)
class FollowerAdmin(DjangoLDPAdmin):
    fields = ['urlid', 'object', 'inbox', 'follower']
    list_display = ['urlid', 'object', 'inbox', 'follower']
    search_fields = ['object', 'inbox', 'follower']


