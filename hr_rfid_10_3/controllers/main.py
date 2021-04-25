# -*- coding: utf-8 -*-
from odoo import http, fields, exceptions, _, SUPERUSER_ID
from odoo.http import request
from enum import Enum

import datetime
import json
import traceback
import psycopg2
import logging
import time

_logger = logging.getLogger(__name__)
