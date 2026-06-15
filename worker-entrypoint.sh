#!/bin/bash
exec celery -A api.tasks.celery_app.app worker --loglevel=info --concurrency=2
