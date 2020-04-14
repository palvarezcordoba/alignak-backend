#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This test check if JWT authentication works
"""

import os
import shlex
import subprocess
import time

import requests
import unittest2


class TestJWT(unittest2.TestCase):
    """
    This class test if JWT authentication works
    """

    @classmethod
    def setUpClass(cls):
        """
        This method:
          * delete mongodb database
          * start the backend with uwsgi
          * authenticates with a JWT

        :return: None
        """
        # Set test mode for Alignak backend
        os.environ['ALIGNAK_BACKEND_TEST'] = '1'
        os.environ['ALIGNAK_BACKEND_MONGO_DBNAME'] = 'alignak-backend-test'
        os.environ['ALIGNAK_BACKEND_CONFIGURATION_FILE'] = './cfg/settings/settings.json'

        # Delete used mongo DBs
        exit_code = subprocess.call(
            shlex.split(
                'mongo %s --eval "db.dropDatabase()"' % os.environ['ALIGNAK_BACKEND_MONGO_DBNAME'])
        )
        assert exit_code == 0

        cls.p = subprocess.Popen(['uwsgi', '--plugin', 'python', '-w', 'alignak_backend.app:app',
                                  '--socket', '0.0.0.0:5500',
                                  '--protocol=http', '--enable-threads', '--pidfile',
                                  '/tmp/uwsgi.pid'])
        time.sleep(3)

        cls.endpoint = 'http://127.0.0.1:5500'

    @classmethod
    def tearDownClass(cls):
        """
        Kill uwsgi

        :return: None
        """
        subprocess.call(['uwsgi', '--stop', '/tmp/uwsgi.pid'])
        time.sleep(2)

    def test_auth(self):
        """Test if we can log in with a JWT

        :return: None
        """
        token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJ1c2VybmFtZSI6ImFkbWluIn0.WKnS2svWExnBoQNnv8LvCk6Fcoqt5hBgYMV3rqbfLNDr4fiPEJKG8Vv9w0N8UbvDh4glnrIBhLNstb_F8IWoYI2ZUKY2LEAPkXkCwMTMab2Yi9-QKW6LMvNfP_-rq409e6Lk4No6WPRLixivzb7FcxuwK13nkrQERHwTYeatoOW_sAVAtaP9DtJF1jYTbHsEVSbbRWXTVM50x1bu6m-faxF8xENY5lAZaUF3949oIm9wkJKtYL6VyvrklsQ91hLeKipnxN9fkru_REhjGpDM211ZhtIkQ9RPakGP7ktKhvo0O-XXZdVOTmyLrdwLMkl9aP5x2by6ibCbhGCJMSwsYLPlqUqL7kZ0LD_UdMJCql4h-OeK-RWGdeVLm1qhQC8BmfR-QOP3dNjkcDzTvWMyYVKbR4jH2Y1BjzI6t8yr8aFGhhuRdPhAzJ_NzWbujgiamwW5K_10qJt3jZ-sewmUBsbAwxcTyn5XPypknZeGUt5kmK948wZyO4NVTvKZzamwIsnRZe_KoNC3sz1lj0zU8gyo-3r2MPh9uNTphdxrKEvavAxYpTyy6qASHSZ-Hdg-_59HjHuYfCWtBRXSHz_5dgWlI3nKbzB-064Zqag-vYNde2XaxlWmdTkoyvWl8qDpJ6T8zpNLFktndjlf6Fq93adZZQw4VLFdVELLY1_xMZ4"
        headers = {'Authorization': 'Bearer {}'.format(token)}
        assert requests.get(self.endpoint, headers=headers).status_code == 200
