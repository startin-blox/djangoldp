from guardian.admin import GuardedModelAdmin
from django.contrib.auth.admin import UserAdmin


class DjangoLDPAdmin(GuardedModelAdmin):
    '''
    An admin model representing a federated object. Inherits from GuardedModelAdmin to provide Django-Guardian
    object-level permissions
    '''
    pass


class DjangoLDPUserAdmin(UserAdmin, GuardedModelAdmin):
    '''An extension of UserAdmin providing the functionality of DjangoLDPAdmin'''
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
