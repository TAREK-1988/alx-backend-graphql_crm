from alx_backend_graphql.settings import *  # noqa

INSTALLED_APPS = list(INSTALLED_APPS) + ["django_crontab"]

CRONJOBS = [
    ("*/5 * * * *", "crm.cron.log_crm_heartbeat"),
]
