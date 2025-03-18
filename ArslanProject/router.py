class KalipMsRouter:
    dies_db = "dies"
    default_db = "default"

    def db_for_read(self, model, **hints):
        """Point database operations for each model to the correct database."""
        model_name = model._meta.model_name
        if model_name == 'KalipMs':
            return self.dies_db
        elif model._meta.app_label == 'DMS':
            return 'dms'
        else:
            return None

    def db_for_write(self, model, **hints):
        """Point database operations for each model to the correct database."""
        model_name = model._meta.model_name
        if model_name == 'KalipMs':
            return 'dies'
        elif model._meta.app_label == 'DMS':
            return 'dms'
        else:
            return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure that migrations occur on the correct database."""
        if app_label == 'DMS':
            return db == 'dms'
        elif model_name == 'KalipMs':
            return db == 'dies'
        else:
            return db == 'default'
        
    def allow_relation(self, obj1, obj2, **hints):
        """Allow any relation if both models are in the same database."""
        if obj1._state.db == obj2._state.db:
            return True
        return None