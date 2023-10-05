import os
from django.apps import AppConfig

class DjangoldpConfig(AppConfig):
    name = 'djangoldp'

    def ready(self):
        self.auto_register_model_admin()
        self.start_activity_queue()
        
        # Patch guardian core to avoid prefetching permissions several times
        from guardian.core import ObjectPermissionChecker
        ObjectPermissionChecker._prefetch_cache_orig = ObjectPermissionChecker._prefetch_cache

        def _prefetch_cache(self):
            if hasattr(self.user, "_guardian_perms_cache"):
                self._obj_perms_cache = self.user._guardian_perms_cache
                return
            self._prefetch_cache_orig()

        ObjectPermissionChecker._prefetch_cache = _prefetch_cache

    def start_activity_queue(self):
        from djangoldp.activities.services import ActivityQueueService
        if os.environ.get('RUN_MAIN') is not None:
            ActivityQueueService.start()

    def auto_register_model_admin(self):
        '''
        Automatically registers Model subclasses in the admin panel (which have not already been added manually)
        '''
        from importlib import import_module

        from django.conf import settings
        from django.contrib import admin
        from djangoldp.admin import DjangoLDPAdmin
        from djangoldp.urls import get_all_non_abstract_subclasses
        from djangoldp.models import Model

        for package in settings.DJANGOLDP_PACKAGES:
            try:
                import_module('{}.admin'.format(package))
            except ModuleNotFoundError:
                pass

        for package in settings.DJANGOLDP_PACKAGES:
            try:
                import_module('{}.models'.format(package))
            except ModuleNotFoundError:
                pass

        for model in get_all_non_abstract_subclasses(Model):
            if not admin.site.is_registered(model):
                admin.site.register(model, DjangoLDPAdmin)
