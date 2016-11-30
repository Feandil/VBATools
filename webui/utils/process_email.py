# Copyright (C) 2016, CERN
# This software is distributed under the terms of the GNU General Public
# Licence version 3 (GPL Version 3), copied verbatim in the file "COPYING".
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as Intergovernmental Organization
# or submit itself to any jurisdiction.

import base64
from email import message_from_string
from email.header import decode_header, make_header
import dateutil.parser

from ..models import Email
from .process_sample import process_file

HEADERS = {
  'Date': 'date',
  'From': 'sender',
  'Message-ID': 'messageid',
  'Subject': 'subject',
  'Return-Path': 'returnpath',
  'User-Agent': 'useragent',
}

def my_parse(msg, email=None):
    if email is None:
        headers = {}
        for key in HEADERS:
            if msg[key]:
                raw = msg[key]
                dst = HEADERS[key]
                try:
                    headers[dst] = unicode(make_header(decode_header(raw)))
                except:
                    pass
        if 'date' in headers:
            headers['date'] = dateutil.parser.parse(headers['date'])
        email = Email(**headers)
    content_subtype = msg.get_content_subtype()
    if (msg.get_content_maintype() == 'application' and (
            content_subtype.endswith('macroEnabled.12') or
            content_subtype.endswith('macroenabled.12') or
            content_subtype == 'msword' or
            content_subtype == 'vnd.ms-powerpoint' or
            content_subtype == 'vnd.ms-excel')):
        filename = msg.get_filename()
        data = msg.get_payload()
        if ('Content-Transfer-Encoding' in msg and
                msg['Content-Transfer-Encoding'].lower() == 'base64'):
            try:
                data = base64.b64decode(data)
            except:
                return
        yield(email, filename, data)
    if not msg.is_multipart():
        return
    if msg.get_content_type() == 'message/rfc822':
        email = None
    for subpart in msg.get_payload():
        for file in my_parse(subpart, email=email):
            yield file

def process_email(raw_email):
    ids = set()
    for (email, filename, data) in my_parse(message_from_string(raw_email)):
        if process_file(data, filename=filename, email=email):
            ids.add(email.id)
    return ids
