import os
import sys
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.conf import settings

from taskstate.models import Task


User = get_user_model()



class Command(BaseCommand):
    """
    Usage:
    python manage.py clear_tasks
    """
    help = 'Clear all tasks in database for dramatiq-taskstate'

    def add_arguments(self, parser):
        parser.add_argument(
            '-y, --yes',
            action='store_true',
            default=None,
            help='Continue without asking confirmation.',
            dest='yes',
        )


    def set_options(self, **options):
        """
        Set instance variables based on an options dict
        """
        self.yes = options['yes']


    def handle(self, **options):
        self.set_options(**options)
        start = True
        if not self.yes:
            yes_no = input('This will delete all tasks in database, are you sure? [y/N]: ')
            start = (
                yes_no == 'yes' or yes_no == 'y'
            )
        if start:
            self.log('\n')
            objs = Task.objects.all().delete()
            msg = 'Deleted {0} tasks'.format(len(objs))
            self.log(msg)
            self.log('\n')
        else:
            raise CommandError('Command cancelled')


    def log(self, msg, level=1):
        self.stdout.write(msg)
