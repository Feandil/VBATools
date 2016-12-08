# Copyright (C) 2016, CERN
# This software is distributed under the terms of the GNU General Public
# Licence version 3 (GPL Version 3), copied verbatim in the file "COPYING".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

from django.conf import settings

import base64
from imaplib2 import IMAP4_SSL
import json
import requests
from time import sleep
from threading import Event

from ..utils import process_email

class EmailFeeder(object):

    def __init__(self, url=None):
        self.mail = settings.EMAIL_FEEDER['SERVER']
        self.username = settings.EMAIL_FEEDER['USERNAME']
        self.password = settings.EMAIL_FEEDER['PASSWORD']
        self.mailbox = settings.EMAIL_FEEDER['MAILBOX']
        self._mail = None
        self.maxbackoff = settings.EMAIL_FEEDER['MAXBACKOFF']
        self.backoff = 2
        self._idlelock = Event()
        self._idlefetch = None
        self._die = False
        if url:
            self.url = '{0}/email/new'.format(url)
        else:
            self.url = None

    def send(self, payload):
        if self.url:
            files = [('emails', ('email.eml', payload, 'message/rfc822'))]
            req = requests.post(self.url, files=files)
            if req.status_code != 200:
                raise RuntimeError('I did not expect this: {0}'.format(req.status_code))
        else:
            process_email(payload)

    def close(self):
        try:
            self._mail.close()
        except:
            pass
        try:
            self._mail.logout()
        except:
            pass
        self._mail = None

    def waitbackoff(self):
        sleep(self.backoff)
        self.backoff *= 2
        if self.backoff > self.maxbackoff:
            self.backoff = self.maxbackoff

    def login(self):
        self.close()
        self.backoff = 2
        while True:
            try:
                self._mail = IMAP4_SSL(self.mail, debug=0)
                break
            except:
                pass
            self.waitbackoff()
        self._mail.login(self.username, self.password)
        (status, _) = self._mail.select(self.mailbox, readonly=False)
        if status != 'OK':
            raise RuntimeError('I did not expect this')
        self.backoff = 2

    def _check_mail(self, id):
        (status, raw_mail) = self._mail.fetch(id, '(RFC822)')
        if status != 'OK':
            raise RuntimeError('I did not expect this')
        assert(len(raw_mail) == 2)
        assert(len(raw_mail[0]) == 2)
        assert('RFC822' in raw_mail[0][0])
        raw_mail = raw_mail[0][1]
        self.send(raw_mail)
        (status, _) = self._mail.store(id, '+FLAGS', '\\Seen')
        if status != 'OK':
            raise RuntimeError('I did not expect this')
        print('processed email {0}'.format(id))

    def check_mails(self):
        (status, ids) = self._mail.search(None, 'UnSeen')
        if status != 'OK':
            raise RuntimeError('I did not expect this')
        ids = ids[0] #For some reason, this is a list...
        if not ids:
            return
        for id in ids.split():
            self._check_mail(id)

    def idle_callback(self, args):
        idlefetch = self._mail.response('FETCH')
        assert(idlefetch[0] == 'FETCH')
        self._idlefetch = idlefetch[1][0]
        if not self._idlelock.isSet():
            self._idlelock.set()

    def run(self):
         while not self._die:
            self.login()
            try:
                lock = Event()
                while not self._die:
                    if self._idlelock.isSet():
                        self._idlelock.clear()
                    self.check_mails()
                    self._mail.idle(timeout=60, callback=self.idle_callback)
                    self._idlelock.wait()
                    if self._idlefetch:
                        # Ignore the flags after the id
                        id = self._idlefetch.split()[0]
                        self._check_mail(id)
                        self._idlefetch = None
            except:
                raise
