from celery import Celery

from app.core.config import settings

celery_app = Celery("bgm_jobs", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_track_started = True
celery_app.conf.broker_connection_retry_on_startup = False
celery_app.conf.broker_connection_timeout = 1
celery_app.conf.redis_socket_connect_timeout = 1
celery_app.conf.redis_socket_timeout = 1
