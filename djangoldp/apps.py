from django.apps import AppConfig
from django.db import OperationalError


class DjangoldpConfig(AppConfig):
    name = 'djangoldp'

    def ready(self):
        self.create_local_source()

    def create_local_source(self):
        from djangoldp.models import LDPSource, Model

        model_classes = {cls.__name__: cls for cls in Model.__subclasses__()}

        for class_name in model_classes:
            model_class = model_classes[class_name]
            if model_class is LDPSource:
                continue
            path = model_class.get_container_path().strip("/")
            try:
                existing_source = LDPSource.objects.get(federation=path)
            except LDPSource.DoesNotExist:
                LDPSource.objects.create(federation=path, urlid=Model.absolute_url(model_class))
            except OperationalError:
                pass

