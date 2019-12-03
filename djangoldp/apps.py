from django.apps import AppConfig
from django.db import OperationalError, connection

class DjangoldpConfig(AppConfig):
    name = 'djangoldp'

    def ready(self):
        self.create_local_source()

    def create_local_source(self):
        from djangoldp.models import LDPSource, Model

        model_classes = {}
        db_tables = []

        for cls in Model.__subclasses__():
            model_classes[cls.__name__] = cls
            db_tables.append(LDPSource.get_meta(cls, "db_table"))

        # Check that all model's table already exists
        existing_tables = connection.introspection.table_names()
        if not all(db_table in existing_tables for db_table in db_tables):
            return

        for class_name in model_classes:
            model_class = model_classes[class_name]
            if model_class is LDPSource:
                continue
            path = model_class.get_container_path().strip("/")
            try:
                LDPSource.objects.get(federation=path)
            except LDPSource.DoesNotExist:
                LDPSource.objects.create(federation=path, urlid=Model.absolute_url(model_class))
            except OperationalError:
                pass

