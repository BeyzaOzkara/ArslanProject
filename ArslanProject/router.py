class KalipMsRouter:
    dies_db = "dies"
    default_db = "default"

    def db_for_read(self, model, **hints):
        model_name = model._meta.model_name
        if model_name == 'KalipMs':
            return self.dies_db
        else:
            return None

    def db_for_write(self, model, **hints):
        model_name = model._meta.model_name
        if model_name == 'KalipMs':
            return 'dies'
        else:
            return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if model_name == 'KalipMs':
            return db == 'dies'
        else:
            return db == 'default'