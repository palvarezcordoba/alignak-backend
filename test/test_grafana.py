#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This test check grafana and create dashboard + graphs
"""

from __future__ import print_function
import os
import json
from datetime import datetime, timedelta
import time
import shlex
from random import randint
import subprocess
import requests
import requests_mock
import unittest2
from bson.objectid import ObjectId
from alignak_backend.grafana import Grafana


class TestGrafana(unittest2.TestCase):
    """
    This class test grafana dashboard and panels
    """

    maxDiff = None

    @classmethod
    def setUpClass(cls):
        """
        This method:
          * delete mongodb database
          * start the backend with uwsgi
          * log in the backend and get the token
          * get the hostgroup

        :return: None
        """
        # Set test mode for Alignak backend
        os.environ['TEST_ALIGNAK_BACKEND'] = '1'
        os.environ['ALIGNAK_BACKEND_MONGO_DBNAME'] = 'alignak-backend-test'

        # Delete used mongo DBs
        exit_code = subprocess.call(
            shlex.split(
                'mongo %s --eval "db.dropDatabase()"' % os.environ['ALIGNAK_BACKEND_MONGO_DBNAME'])
        )
        assert exit_code == 0

        cls.p = subprocess.Popen(['uwsgi', '--plugin', 'python', '-w', 'alignak_backend.app:app',
                                  '--socket', '0.0.0.0:5000',
                                  '--protocol=http', '--enable-threads', '--pidfile',
                                  '/tmp/uwsgi.pid', '--logto=/tmp/alignak_backend.log'])
        # cls.p = subprocess.Popen(['alignak-backend'])
        time.sleep(3)

        cls.endpoint = 'http://127.0.0.1:5000'

        headers = {'Content-Type': 'application/json'}
        params = {'username': 'admin', 'password': 'admin', 'action': 'generate'}
        # get token
        response = requests.post(cls.endpoint + '/login', json=params, headers=headers)
        resp = response.json()
        cls.token = resp['token']
        cls.auth = requests.auth.HTTPBasicAuth(cls.token, '')

        # Get default realm
        response = requests.get(cls.endpoint + '/realm', auth=cls.auth)
        resp = response.json()
        cls.realm_all = resp['_items'][0]['_id']

        data = {"name": "All A", "_parent": cls.realm_all}
        response = requests.post(cls.endpoint + '/realm', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.realmAll_A = resp['_id']

        data = {"name": "All A1", "_parent": cls.realmAll_A}
        response = requests.post(cls.endpoint + '/realm', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.realmAll_A1 = resp['_id']

        data = {"name": "All B", "_parent": cls.realm_all}
        response = requests.post(cls.endpoint + '/realm', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.realmAll_B = resp['_id']

        # Get admin user
        response = requests.get(cls.endpoint + '/user', {"name": "admin"}, auth=cls.auth)
        resp = response.json()
        cls.user_admin = resp['_items'][0]['_id']

    @classmethod
    def tearDownClass(cls):
        """
        Kill uwsgi

        :return: None
        """
        subprocess.call(['uwsgi', '--stop', '/tmp/uwsgi.pid'])
        # cls.p.kill()
        time.sleep(2)
        os.unlink("/tmp/alignak_backend.log")

    @classmethod
    def setUp(cls):
        """
        Delete resources in backend

        :return: None
        """
        headers = {'Content-Type': 'application/json'}

        # Add command
        data = json.loads(open('cfg/command_ping.json').read())
        data['_realm'] = cls.realm_all
        requests.post(cls.endpoint + '/command', json=data, headers=headers, auth=cls.auth)
        response = requests.get(cls.endpoint + '/command', auth=cls.auth)
        resp = response.json()
        rc = resp['_items']

        # Add an host
        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[0]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = cls.realm_all
        data['ls_last_check'] = int(time.time())
        data['ls_perf_data'] = "rta=14.581000ms;1000.000000;3000.000000;0.000000 pl=0%;100;100;0"
        response = requests.post(cls.endpoint + '/host', json=data, headers=headers, auth=cls.auth)
        resp = response.json()
        response = requests.get(cls.endpoint + '/host/' + resp['_id'], auth=cls.auth)
        cls.host_srv001 = response.json()

        # Add a service
        data = json.loads(open('cfg/service_srv001_ping.json').read())
        data['host'] = cls.host_srv001['_id']
        data['check_command'] = rc[0]['_id']
        data['_realm'] = cls.realm_all
        data['name'] = 'load'
        data['ls_last_check'] = int(time.time())
        data['ls_perf_data'] = "load1=0.360;15.000;30.000;0; load5=0.420;10.000;25.000;0; " \
                               "load15=0.340;5.000;20.000;0;"
        response = requests.post(cls.endpoint + '/service', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.host_srv001_srv = resp['_id']

        # Add an host in realm A1
        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[0]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = cls.realmAll_A1
        data['name'] = "srv002"
        data['alias'] = "Server #2"
        data['tags'] = ["t2"]
        data['ls_last_check'] = int(time.time())
        data['ls_perf_data'] = "rta=14.581000ms;1000.000000;3000.000000;0.000000 pl=0%;100;100;0"
        response = requests.post(cls.endpoint + '/host', json=data, headers=headers, auth=cls.auth)
        resp = response.json()
        response = requests.get(cls.endpoint + '/host/' + resp['_id'], auth=cls.auth)
        cls.host_srv002 = response.json()

        # Add a service for srv002
        data = json.loads(open('cfg/service_srv001_ping.json').read())
        data['host'] = cls.host_srv002['_id']
        data['check_command'] = rc[0]['_id']
        data['_realm'] = cls.realmAll_A1
        data['name'] = 'load'
        data['ls_last_check'] = int(time.time())
        data['ls_perf_data'] = "load1=0.360;15.000;30.000;0; load5=0.420;10.000;25.000;0; " \
                               "load15=0.340;5.000;20.000;0;"
        response = requests.post(cls.endpoint + '/service', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        response = requests.get(cls.endpoint + '/service/' + resp['_id'], auth=cls.auth)
        cls.host_srv002_srv = response.json()

    @classmethod
    def tearDown(cls):
        """
        Delete resources in backend

        :return: None
        """
        for resource in ['host', 'service', 'command', 'history',
                         'actionacknowledge', 'actiondowntime', 'actionforcecheck', 'grafana',
                         'graphite', 'influxdb']:
            requests.delete(cls.endpoint + '/' + resource, auth=cls.auth)

    def test_grafana_on_realms(self):
        """We can have more than 1 grafana server on each realm

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        # add a grafana on realm A + subrealm
        data = {
            'name': 'grafana All A+',
            'address': '192.168.0.100',
            'apikey': 'xxxxxxxxxxxx0',
            '_realm': self.realmAll_A,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/grafana', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # add a grafana on realm All
        data = {
            'name': 'grafana All',
            'address': '192.168.0.101',
            'apikey': 'xxxxxxxxxxxx1',
            '_realm': self.realm_all,
            '_sub_realm': False
        }
        response = requests.post(self.endpoint + '/grafana', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        grafana_all = resp['_id']

        # update the grafana on realm All + subrealm
        data = {'_sub_realm': True}
        headers_up = {
            'Content-Type': 'application/json',
            'If-Match': resp['_etag']
        }
        response = requests.patch(self.endpoint + '/grafana/' + grafana_all, json=data,
                                  headers=headers_up, auth=self.auth)
        self.assertEqual('OK', resp['_status'], resp)
        resp = response.json()

        # delete grafana on realm All
        headers_delete = {
            'Content-Type': 'application/json',
            'If-Match': resp['_etag']
        }
        response = requests.delete(self.endpoint + '/grafana/' + resp['_id'],
                                   headers=headers_delete, auth=self.auth)
        self.assertEqual(response.status_code, 204)

        response = requests.get(self.endpoint + '/grafana', auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 1)

        # add grafana on realm All + subrealm
        data = {
            'name': 'grafana All',
            'address': '192.168.0.101',
            'apikey': 'xxxxxxxxxxxx1',
            '_realm': self.realm_all,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/grafana', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

    def test_2_graphites_same_realm(self):
        """Test 2 graphite on same realm, but only one can be affected to grafana on same realm

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        # Add grafana All + subrealms
        data = {
            'name': 'grafana All',
            'address': '192.168.0.101',
            'apikey': 'xxxxxxxxxxxx1',
            '_realm': self.realm_all,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/grafana', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        grafana_all = resp['_id']

        # Add graphite_A in realm A associate to grafana
        data = {
            'name': 'graphite A sub',
            'carbon_address': '192.168.0.102',
            'graphite_address': '192.168.0.102',
            'prefix': 'my_A_sub',
            'grafana': grafana_all,
            '_realm': self.realmAll_A,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/graphite', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # Add graphite_B in realm A associate to grafana, so graphite_A not linked
        data = {
            'name': 'graphite B',
            'carbon_address': '192.168.0.101',
            'graphite_address': '192.168.0.101',
            'prefix': 'my_B',
            'grafana': grafana_all,
            '_realm': self.realmAll_A
        }
        response = requests.post(self.endpoint + '/graphite', json=data, headers=headers,
                                 auth=self.auth)
        assert response.status_code == 412

        # todo try add in realm A1
        data = {
            'name': 'graphite B',
            'carbon_address': '192.168.0.101',
            'graphite_address': '192.168.0.101',
            'prefix': 'my_B',
            'grafana': grafana_all,
            '_realm': self.realmAll_A1
        }
        requests.post(self.endpoint + '/graphite', json=data, headers=headers, auth=self.auth)

    def test_grafana_annotations_error(self):
        """
        Get annotations with some errors

        :return: None
        """
        headers = {'Content-Type': 'application/json'}

        # Request some annotations
        # Time frame for the request - whatever, this endpoint do not care about the time frame!!!
        now = datetime.utcnow()
        range_to = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
        past = now - timedelta(days=5)
        range_from = past.strftime('%a, %d %b %Y %H:%M:%S GMT')

        # Grafana request for some annotations
        # Error on syntax
        data = {
            u'range': {
                u'from': range_from,
                u'to': range_to,
                # Ignored...
                u'raw': {u'to': u'now', u'from': u'now-6h'}
            },
            # Ignored...
            u'rangeRaw': {u'to': u'now', u'from': u'now-6h'},
            u'annotation': {
                # Request bad query !
                u'query': u'fake',
                # 4 ignored fields...
                u'iconColor': u'rgba(255, 96, 96, 1)',
                u'enable': True,
                u'name': u'Host alerts',
                u'datasource': u'Backend'
            }
        }
        response = requests.post(self.endpoint + '/annotations',
                                 json=data, headers=headers, auth=self.auth)
        resp = response.json()
        print(resp)
        assert "_error" in resp
        assert resp["_error"]["message"] == u"Bad format for query: fake. " \
                                            u"Query must be something like endpoint:type:target."

        # Grafana request for some annotations
        # Error on endpoint
        data = {
            u'range': {
                u'from': range_from,
                u'to': range_to,
                # Ignored...
                u'raw': {u'to': u'now', u'from': u'now-6h'}
            },
            # Ignored...
            u'rangeRaw': {u'to': u'now', u'from': u'now-6h'},
            u'annotation': {
                # Request bad query !
                u'query': u'fake:whatever:{srv001}',
                # 4 ignored fields...
                u'iconColor': u'rgba(255, 96, 96, 1)',
                u'enable': True,
                u'name': u'Host alerts',
                u'datasource': u'Backend'
            }
        }
        response = requests.post(self.endpoint + '/annotations',
                                 json=data, headers=headers, auth=self.auth)
        resp = response.json()
        print(resp)
        assert "_error" in resp
        assert resp["_error"]["message"] == u"Bad endpoint for query: fake:whatever:{srv001}. " \
                                            u"Only history and livestate are available."

    def test_grafana_history_annotations(self):
        """
        Get annotations from history

        :return: None
        """
        headers = {'Content-Type': 'application/json'}

        # Create an event in the history
        data = {
            'host_name': "test",
            "service_name": "service",
            'user': None,
            'type': 'monitoring.alert',
            'message': "Test event #1 for an alert"
        }
        response = requests.post(self.endpoint + '/history',
                                 json=data, headers=headers, auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # Wait 1 second
        time.sleep(1)

        # Create an event in the history
        data = {
            'host_name': "test1",
            'user': None,
            'type': 'monitoring.alert',
            'message': "Test event #2 for an alert"
        }
        response = requests.post(self.endpoint + '/history',
                                 json=data, headers=headers, auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # Wait 1 second
        time.sleep(1)

        # Create an event in the history
        data = {
            'host_name': "test2",
            'user': None,
            'type': 'monitoring.alert',
            'message': "Test event #3 for an alert"
        }
        response = requests.post(self.endpoint + '/history',
                                 json=data, headers=headers, auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # Wait 1 second
        time.sleep(1)

        # Create an event now in the history
        data = {
            'host_name': "test2",
            'user': None,
            'type': 'monitoring.notification',
            'message': "Test event #4 for an alert"
        }
        response = requests.post(self.endpoint + '/history',
                                 json=data, headers=headers, auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # Request some annotations
        # 1- no results within the time frame
        # Time frame for the request
        now = datetime.utcnow()
        range_to = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
        # Only one second in the past
        past = now - timedelta(seconds=1)
        range_from = past.strftime('%a, %d %b %Y %H:%M:%S GMT')
        print("Date from: %s, to: %s" % (range_from, range_to))

        # Grafana request for some annotations
        data = {
            u'range': {
                u'from': range_from,
                u'to': range_to,
                # Ignored...
                u'raw': {u'to': u'now', u'from': u'now-6h'}
            },
            # Ignored...
            u'rangeRaw': {u'to': u'now', u'from': u'now-6h'},
            u'annotation': {
                # Request for alerts of hosts test and test1
                u'query': u'history:monitoring.alert:{test,test1}',
                # 4 ignored fields...
                u'iconColor': u'rgba(255, 96, 96, 1)',
                u'enable': True,
                u'name': u'Host alerts',
                u'datasource': u'Backend'
            }
        }
        response = requests.post(self.endpoint + '/annotations',
                                 json=data, headers=headers, auth=self.auth)
        print("Response: %s" % response)
        resp = response.json()
        # No items in the response
        print("Response :%s" % resp)
        self.assertEqual(len(resp), 0)

        # Request some annotations
        # 2- with results in the time frame
        # Time frame for the request
        now = datetime.utcnow()
        range_to = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
        # Five seconds in the past
        past = now - timedelta(seconds=5)
        range_from = past.strftime('%a, %d %b %Y %H:%M:%S GMT')
        print("Date from: %s, to: %s" % (range_from, range_to))

        # Grafana request for some annotations
        data = {
            u'range': {
                u'from': range_from,
                u'to': range_to,
                # Ignored...
                u'raw': {u'to': u'now', u'from': u'now-6h'}
            },
            # Ignored...
            u'rangeRaw': {u'to': u'now', u'from': u'now-6h'},
            u'annotation': {
                # Request for alerts of hosts test and test1
                u'query': u'history:monitoring.alert:{test,test1}',
                # 4 ignored fields...
                u'iconColor': u'rgba(255, 96, 96, 1)',
                u'enable': True,
                u'name': u'Host alerts',
                u'datasource': u'Backend'
            }
        }
        response = requests.post(self.endpoint + '/annotations',
                                 json=data, headers=headers, auth=self.auth)
        resp = response.json()
        # Grafana expects a response containing an array of annotation objects
        # in the following format:
        # [
        #   {
        #     annotation: annotation, // The original annotation sent from Grafana.
        #     time: time, // Time since UNIX Epoch in milliseconds. (required)
        #     title: title, // The title for the annotation tooltip. (required)
        #     tags: tags, // Tags for the annotation. (optional)
        #     text: text // Text for the annotation. (optional)
        #   }
        # ]

        # Two items in the response
        self.assertEqual(len(resp), 2)

        # All expected data fields are present
        rsp = resp[0]
        self.assertIn('annotation', rsp)
        self.assertEqual(rsp['annotation'], data['annotation'])
        self.assertIn('time', rsp)
        self.assertIn('title', rsp)
        self.assertEqual(rsp['title'], "test/service - Test event #1 for an alert")
        self.assertIn('tags', rsp)
        self.assertEqual(rsp['tags'], ["monitoring.alert"])
        self.assertIn('text', rsp)
        self.assertEqual(rsp['text'], "Test event #1 for an alert")

        rsp = resp[1]
        self.assertIn('annotation', rsp)
        self.assertEqual(rsp['annotation'], data['annotation'])
        self.assertIn('time', rsp)
        self.assertIn('title', rsp)
        self.assertEqual(rsp['title'], "test1 - Test event #2 for an alert")
        self.assertIn('tags', rsp)
        self.assertEqual(rsp['tags'], ["monitoring.alert"])
        self.assertIn('text', rsp)
        self.assertEqual(rsp['text'], "Test event #2 for an alert")

        # Request some annotations
        # 3- for one host only
        # Grafana request for some annotations
        data = {
            u'range': {
                u'from': range_from,
                u'to': range_to,
            },
            u'annotation': {
                # Request for alerts of hosts test and test1
                u'query': u'history:monitoring.alert:test',
            }
        }
        response = requests.post(self.endpoint + '/annotations',
                                 json=data, headers=headers, auth=self.auth)
        resp = response.json()
        # One item in the response
        self.assertEqual(len(resp), 1)

        # All expected data fields are present
        rsp = resp[0]
        self.assertIn('annotation', rsp)
        self.assertEqual(rsp['annotation'], data['annotation'])
        self.assertIn('time', rsp)
        self.assertIn('title', rsp)
        self.assertEqual(rsp['title'], "test/service - Test event #1 for an alert")
        self.assertIn('tags', rsp)
        self.assertEqual(rsp['tags'], ["monitoring.alert"])
        self.assertIn('text', rsp)
        self.assertEqual(rsp['text'], "Test event #1 for an alert")

        # Request some annotations
        # 4- for one host specific service
        # Grafana request for some annotations
        data = {
            u'range': {
                u'from': range_from,
                u'to': range_to,
            },
            # Ignored...
            u'annotation': {
                # Request for alerts of the service "service" for the host "test"
                u'query': u'history:monitoring.alert:test:service',
            }
        }
        response = requests.post(self.endpoint + '/annotations',
                                 json=data, headers=headers, auth=self.auth)
        resp = response.json()
        # One item in the response
        self.assertEqual(len(resp), 1)

        # All expected data fields are present
        rsp = resp[0]
        self.assertIn('annotation', rsp)
        self.assertEqual(rsp['annotation'], data['annotation'])
        self.assertIn('time', rsp)
        self.assertIn('title', rsp)
        self.assertEqual(rsp['title'], "test/service - Test event #1 for an alert")
        self.assertIn('tags', rsp)
        self.assertEqual(rsp['tags'], ["monitoring.alert"])
        self.assertIn('text', rsp)
        self.assertEqual(rsp['text'], "Test event #1 for an alert")

        # Request some annotations
        # 5- unknown event
        # Grafana request for some annotations
        data = {
            u'range': {
                u'from': range_from,
                u'to': range_to,
            },
            # Ignored...
            u'annotation': {
                # Request for alerts of the host test
                u'query': u'history:fake.event:test',
            }
        }
        response = requests.post(self.endpoint + '/annotations',
                                 json=data, headers=headers, auth=self.auth)
        resp = response.json()
        # One item in the response
        self.assertEqual(len(resp), 0)

    def test_grafana_livestate_annotations(self):
        """
        Get annotations from livestate

        :return: None
        """
        headers = {'Content-Type': 'application/json'}

        # Request some annotations
        # 2- with results in the time frame
        # Time frame for the request - whatever, this endpoint do not car about the time frame!!!
        now = datetime.utcnow()
        range_to = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
        # One day in the past
        past = now - timedelta(days=5)
        range_from = past.strftime('%a, %d %b %Y %H:%M:%S GMT')

        # Grafana request for some annotations
        data = {
            u'range': {
                u'from': range_from,
                u'to': range_to,
                # Ignored...
                u'raw': {u'to': u'now', u'from': u'now-6h'}
            },
            # Ignored...
            u'rangeRaw': {u'to': u'now', u'from': u'now-6h'},
            u'annotation': {
                # Request for livestate of hosts srv001
                u'query': u'livestate:whatever:{srv001}',
                # 4 ignored fields...
                u'iconColor': u'rgba(255, 96, 96, 1)',
                u'enable': True,
                u'name': u'Host alerts',
                u'datasource': u'Backend'
            }
        }
        response = requests.post(self.endpoint + '/annotations',
                                 json=data, headers=headers, auth=self.auth)
        resp = response.json()
        # Grafana expects a response containing an array of annotation objects
        # in the following format:
        # [
        #   {
        #     annotation: annotation, // The original annotation sent from Grafana.
        #     time: time, // Time since UNIX Epoch in milliseconds. (required)
        #     title: title, // The title for the annotation tooltip. (required)
        #     tags: tags, // Tags for the annotation. (optional)
        #     text: text // Text for the annotation. (optional)
        #   }
        # ]

        # One item in the response
        self.assertEqual(len(resp), 1)

        # All expected data fields are present
        rsp = resp[0]
        self.assertIn('annotation', rsp)
        self.assertEqual(rsp['annotation'], data['annotation'])
        self.assertIn('time', rsp)
        self.assertIn('title', rsp)
        self.assertEqual(rsp['title'], "Server #1")  # Alias
        self.assertIn('tags', rsp)
        self.assertEqual(rsp['tags'], ["t1", "t2"])  # Tags
        self.assertIn('text', rsp)
        self.assertEqual(rsp['text'], "srv001: UNREACHABLE (HARD) - ")     # Live state

        # Request some annotations
        # 3- for one host only
        # Grafana request for some annotations
        data = {
            u'range': {
                u'from': range_from,
                u'to': range_to,
            },
            u'annotation': {
                # Request for livestate of hosts srv001 and srv002
                u'query': u'livestate:whatever:{srv001,srv002}',
            }
        }
        response = requests.post(self.endpoint + '/annotations',
                                 json=data, headers=headers, auth=self.auth)
        resp = response.json()
        # One item in the response
        self.assertEqual(len(resp), 2)

        # All expected data fields are present
        rsp = resp[0]
        self.assertIn('annotation', rsp)
        self.assertEqual(rsp['annotation'], data['annotation'])
        self.assertIn('time', rsp)
        self.assertIn('title', rsp)
        self.assertEqual(rsp['title'], "Server #1")  # Alias
        self.assertIn('tags', rsp)
        self.assertEqual(rsp['tags'], ["t1", "t2"])  # Tags
        self.assertIn('text', rsp)
        self.assertEqual(rsp['text'], "srv001: UNREACHABLE (HARD) - ")

        rsp = resp[1]
        self.assertIn('annotation', rsp)
        self.assertEqual(rsp['annotation'], data['annotation'])
        self.assertIn('time', rsp)
        self.assertIn('title', rsp)
        self.assertEqual(rsp['title'], "Server #2")     # Alias
        self.assertIn('tags', rsp)
        self.assertEqual(rsp['tags'], ["t2"])           # Tags
        self.assertIn('text', rsp)
        self.assertEqual(rsp['text'], "srv002: UNREACHABLE (HARD) - ")

    def test_create_dashboard_panels_graphite(self):
        # pylint: disable=too-many-locals
        """
        Create dashboard into grafana with datasource graphite

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        # Create grafana in realm All + subrealm
        data = {
            'name': 'grafana All',
            'address': '192.168.0.101',
            'apikey': 'xxxxxxxxxxxx1',
            '_realm': self.realm_all,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/grafana', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        print("Grafana All: %s" % resp)
        grafana_all = resp['_id']

        # Create statsd in realm All + subrealm
        data = {
            'name': 'statsd All',
            'address': '192.168.0.101',
            'port': 8125,
            'prefix': 'alignak-statsd',
            '_realm': self.realm_all,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/statsd', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        statsd_all = resp['_id']

        # Create a graphite in All B linked to grafana
        data = {
            'name': 'graphite B',
            'carbon_address': '192.168.0.101',
            'graphite_address': '192.168.0.101',
            'prefix': 'my_B',
            'grafana': grafana_all,
            'statsd': statsd_all,
            '_realm': self.realmAll_B
        }
        response = requests.post(self.endpoint + '/graphite', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # Create a graphite in All A + subrealm liked to grafana
        data = {
            'name': 'graphite A sub',
            'carbon_address': '192.168.0.102',
            'graphite_address': '192.168.0.102',
            'prefix': 'my_A_sub',
            'grafana': grafana_all,
            '_realm': self.realmAll_A,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/graphite', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # test grafana class and code to create dashboard in grafana
        from alignak_backend.app import app, current_app
        with app.app_context():
            grafana_db = current_app.data.driver.db['grafana']
            grafanas = grafana_db.find()
            for grafana in grafanas:
                with requests_mock.mock() as mockreq:
                    ret = [{"id": 1, "orgId": 1, "name": 'alignak-graphite-graphite B',
                            "type": "grafana-simple-json-datasource",
                            "typeLogoUrl": "public/plugins/grafana-simple-json-datasource/src/img/"
                                           "simpleJson_logo.svg",
                            "access": "proxy", "url": "http://127.0.0.1/glpi090/apirest.php",
                            "password": "", "user": "", "database": "", "basicAuth": True,
                            "basicAuthUser": "", "basicAuthPassword": "", "withCredentials": False,
                            "isDefault": False}]
                    mockreq.get('http://192.168.0.101:3000/api/datasources', json=ret)
                    mockreq.post('http://192.168.0.101:3000/api/datasources',
                                 json={'id': randint(2, 10)})
                    graf = Grafana(grafana)
                    assert len(graf.datasources) == 2
                    assert len(graf.timeseries) == 3
                    assert sorted([ObjectId(self.realmAll_B), ObjectId(self.realmAll_A),
                                   ObjectId(self.realmAll_A1)]) == sorted(graf.timeseries.keys())
                    for ts in graf.timeseries:
                        assert isinstance(ts, ObjectId)
                        assert graf.timeseries[ts]
                        print("TS: %s - %s - %s - %s" % (ts,
                                                         graf.timeseries[ts]['_realm'],
                                                         graf.timeseries[ts]['name'],
                                                         graf.timeseries[ts]['_id']))

                    assert graf.timeseries[ObjectId(self.realmAll_A)]['name'] == 'graphite A sub'
                    assert graf.timeseries[ObjectId(self.realmAll_A1)]['name'] == 'graphite A sub'
                    assert graf.timeseries[ObjectId(self.realmAll_A1)]['ts_prefix'] == \
                        'my_A_sub'
                    assert graf.timeseries[ObjectId(self.realmAll_A1)]['statsd_prefix'] == ''
                    assert graf.timeseries[ObjectId(self.realmAll_A1)]['type'] == 'graphite'

                    assert graf.timeseries[ObjectId(self.realmAll_B)]['name'] == 'graphite B'
                    assert graf.timeseries[ObjectId(self.realmAll_B)]['ts_prefix'] == 'my_B'
                    assert graf.timeseries[ObjectId(self.realmAll_B)]['statsd_prefix'] == \
                        'alignak-statsd'
                    assert graf.timeseries[ObjectId(self.realmAll_B)]['type'] == 'graphite'
                history = mockreq.request_history
                methods = {'POST': 0, 'GET': 0}
                for h in history:
                    methods[h.method] += 1
                # One datasources created because we simulated that on still exists
                assert {'POST': 1, 'GET': 1} == methods

                # Create a dashboard for an host!
                with app.test_request_context():
                    with requests_mock.mock() as mockreq:
                        ret = [{"id": 1, "orgId": 1, "name": 'alignak-graphite-graphite B',
                                "type": "grafana-simple-json-datasource",
                                "typeLogoUrl": "public/plugins/grafana-simple-json-datasource/src/"
                                               "img/simpleJson_logo.svg",
                                "access": "proxy", "url": "http://127.0.0.1/glpi090/apirest.php",
                                "password": "", "user": "", "database": "", "basicAuth": True,
                                "basicAuthUser": "", "basicAuthPassword": "",
                                "withCredentials": False, "isDefault": True},
                               {"id": 2, "orgId": 1, "name": 'alignak-graphite-graphite A sub',
                                "type": "grafana-simple-json-datasource",
                                "typeLogoUrl": "public/plugins/grafana-simple-json-datasource/src/"
                                               "img/simpleJson_logo.svg",
                                "access": "proxy", "url": "http://127.0.0.1/glpi090/apirest.php",
                                "password": "", "user": "", "database": "", "basicAuth": True,
                                "basicAuthUser": "", "basicAuthPassword": "",
                                "withCredentials": False, "isDefault": False}]
                        mockreq.get('http://192.168.0.101:3000/api/datasources', json=ret)
                        mockreq.post('http://192.168.0.101:3000/api/datasources',
                                     json={'id': randint(2, 10)})
                        mockreq.post('http://192.168.0.101:3000/api/datasources/db', json='true')
                        mockreq.post('http://192.168.0.101:3000/api/dashboards/db', json='true')
                        graf = Grafana(grafana)
                        for ts in graf.timeseries:
                            print("TS: %s - %s - %s - %s" % (ts,
                                                             graf.timeseries[ts]['_realm'],
                                                             graf.timeseries[ts]['name'],
                                                             graf.timeseries[ts]['_id']))
                        # The host is not in a managed realm
                        assert self.host_srv001['_realm'] == self.realm_all
                        # Must convert to ObjectId because we are not really in Eve :)
                        self.host_srv001['_realm'] = ObjectId(self.host_srv001['_realm'])
                        assert self.host_srv001['_realm'] not in graf.timeseries.keys()
                        assert not graf.create_dashboard(self.host_srv001)

                        assert self.host_srv002['_realm'] == self.realmAll_A1
                        # Must convert to ObjectId because we are not really in Eve :)
                        self.host_srv002['_realm'] = ObjectId(self.host_srv002['_realm'])
                        assert ObjectId(self.host_srv002['_realm']) in graf.timeseries.keys()
                        assert graf.create_dashboard(self.host_srv002)
                        history = mockreq.request_history
                        methods = {'POST': 0, 'GET': 0}
                        for h in history:
                            methods[h.method] += 1
                            if h.method == 'POST':
                                dash = h.json()
                                print("Post response: %s" % dash)
                                # assert len(dash['dashboard']['rows']) == 2
                        assert {'POST': 1, 'GET': 1} == methods

                    # check host and the service are tagged grafana and have the id
                    host_db = current_app.data.driver.db['host']
                    host002 = host_db.find_one({'_id': ObjectId(self.host_srv002['_id'])})
                    assert host002['ls_grafana']
                    assert host002['ls_grafana_panelid'] == 1
                    service_db = current_app.data.driver.db['service']
                    srv002 = service_db.find_one({'_id': ObjectId(self.host_srv002_srv['_id'])})
                    print("Service: %s" % srv002)
                    assert srv002['ls_grafana']
                    assert srv002['ls_grafana_panelid'] == 2

    def test_create_dashboard_panels_influxdb(self):
        # pylint: disable=too-many-locals
        """
        Create dashboard into grafana with datasource influxdb

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        # Create grafana in realm All + subrealm
        data = {
            'name': 'grafana All',
            'address': '192.168.0.101',
            'apikey': 'xxxxxxxxxxxx1',
            '_realm': self.realm_all,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/grafana', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        print("Grafana All: %s" % resp)
        grafana_all = resp['_id']

        # Create statsd in realm All + subrealm
        data = {
            'name': 'statsd influx All',
            'address': '192.168.0.101',
            'port': 8125,
            'prefix': 'alignak-statsd',
            '_realm': self.realm_all,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/statsd', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        statsd_all = resp['_id']

        # Create an influxdb in All B linked to grafana
        data = {
            'name': 'influxdb B',
            'address': '192.168.0.101',
            'port': 8086,
            'database': 'alignak',
            'login': 'alignak',
            'password': 'alignak',
            'prefix': 'my_B',
            'grafana': grafana_all,
            'statsd': statsd_all,
            '_realm': self.realmAll_B
        }
        response = requests.post(self.endpoint + '/influxdb', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # Create an influxdb in All A + subrealm liked to grafana
        data = {
            'name': 'influxdb A sub',
            'address': '192.168.0.102',
            'port': 8086,
            'database': 'alignak',
            'login': 'alignak',
            'password': 'alignak',
            'prefix': 'my_A_sub',
            'grafana': grafana_all,
            '_realm': self.realmAll_A,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/influxdb', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # test grafana class and code to create dashboard in grafana
        from alignak_backend.app import app, current_app
        with app.app_context():
            grafana_db = current_app.data.driver.db['grafana']
            grafanas = grafana_db.find()
            for grafana in grafanas:
                with requests_mock.mock() as mockreq:
                    ret = [{"id": 1, "orgId": 1, "name": 'alignak-influxdb-influxdb B',
                            "type": "grafana-simple-json-datasource",
                            "typeLogoUrl": "public/plugins/grafana-simple-json-datasource/src/img/"
                                           "simpleJson_logo.svg",
                            "access": "proxy", "url": "http://127.0.0.1/glpi090/apirest.php",
                            "password": "", "user": "", "database": "", "basicAuth": True,
                            "basicAuthUser": "", "basicAuthPassword": "", "withCredentials": False,
                            "isDefault": False}]
                    mockreq.get('http://192.168.0.101:3000/api/datasources', json=ret)
                    mockreq.post('http://192.168.0.101:3000/api/datasources',
                                 json={'id': randint(2, 10)})
                    graf = Grafana(grafana)
                    assert len(graf.datasources) == 2
                    assert len(graf.timeseries) == 3
                    assert sorted([ObjectId(self.realmAll_B), ObjectId(self.realmAll_A),
                                   ObjectId(self.realmAll_A1)]) == sorted(graf.timeseries.keys())
                    for ts in graf.timeseries:
                        assert isinstance(ts, ObjectId)
                        assert graf.timeseries[ts]
                        print("TS: %s - %s - %s - %s" % (ts,
                                                         graf.timeseries[ts]['_realm'],
                                                         graf.timeseries[ts]['name'],
                                                         graf.timeseries[ts]['_id']))

                    assert graf.timeseries[ObjectId(self.realmAll_A)]['name'] == 'influxdb A sub'
                    assert graf.timeseries[ObjectId(self.realmAll_A1)]['name'] == 'influxdb A sub'
                    assert graf.timeseries[ObjectId(self.realmAll_A1)]['ts_prefix'] == \
                        'my_A_sub'
                    assert graf.timeseries[ObjectId(self.realmAll_A1)]['statsd_prefix'] == ''
                    assert graf.timeseries[ObjectId(self.realmAll_A1)]['type'] == 'influxdb'

                    assert graf.timeseries[ObjectId(self.realmAll_B)]['name'] == 'influxdb B'
                    assert graf.timeseries[ObjectId(self.realmAll_B)]['ts_prefix'] == 'my_B'
                    assert graf.timeseries[ObjectId(self.realmAll_B)]['statsd_prefix'] == \
                        'alignak-statsd'
                    assert graf.timeseries[ObjectId(self.realmAll_B)]['type'] == 'influxdb'
                history = mockreq.request_history
                methods = {'POST': 0, 'GET': 0}
                for h in history:
                    methods[h.method] += 1
                # One datasources created because we simulated that on still exists
                assert {'POST': 1, 'GET': 1} == methods

                # Create a dashboard for an host!
                with app.test_request_context():
                    with requests_mock.mock() as mockreq:
                        ret = [{"id": 1, "orgId": 1, "name": 'alignak-influxdb-influxdb B',
                                "type": "grafana-simple-json-datasource",
                                "typeLogoUrl": "public/plugins/grafana-simple-json-datasource/src/"
                                               "img/simpleJson_logo.svg",
                                "access": "proxy", "url": "http://127.0.0.1/glpi090/apirest.php",
                                "password": "", "user": "", "database": "", "basicAuth": True,
                                "basicAuthUser": "", "basicAuthPassword": "",
                                "withCredentials": False, "isDefault": True},
                               {"id": 2, "orgId": 1, "name": 'alignak-influxdb-influxdb A sub',
                                "type": "grafana-simple-json-datasource",
                                "typeLogoUrl": "public/plugins/grafana-simple-json-datasource/src/"
                                               "img/simpleJson_logo.svg",
                                "access": "proxy", "url": "http://127.0.0.1/glpi090/apirest.php",
                                "password": "", "user": "", "database": "", "basicAuth": True,
                                "basicAuthUser": "", "basicAuthPassword": "",
                                "withCredentials": False, "isDefault": False}]
                        mockreq.get('http://192.168.0.101:3000/api/datasources', json=ret)
                        mockreq.post('http://192.168.0.101:3000/api/datasources',
                                     json={'id': randint(2, 10)})
                        mockreq.post('http://192.168.0.101:3000/api/datasources/db', json='true')
                        mockreq.post('http://192.168.0.101:3000/api/dashboards/db', json='true')
                        graf = Grafana(grafana)
                        for ts in graf.timeseries:
                            print("TS: %s - %s - %s - %s" % (ts,
                                                             graf.timeseries[ts]['_realm'],
                                                             graf.timeseries[ts]['name'],
                                                             graf.timeseries[ts]['_id']))
                        # The host is not in a managed realm
                        assert self.host_srv001['_realm'] == self.realm_all
                        # Must convert to ObjectId because we are not really in Eve :)
                        self.host_srv001['_realm'] = ObjectId(self.host_srv001['_realm'])
                        assert self.host_srv001['_realm'] not in graf.timeseries.keys()
                        assert not graf.create_dashboard(self.host_srv001)

                        assert self.host_srv002['_realm'] == self.realmAll_A1
                        # Must convert to ObjectId because we are not really in Eve :)
                        self.host_srv002['_realm'] = ObjectId(self.host_srv002['_realm'])
                        assert ObjectId(self.host_srv002['_realm']) in graf.timeseries.keys()
                        assert graf.create_dashboard(self.host_srv002)
                        history = mockreq.request_history
                        methods = {'POST': 0, 'GET': 0}
                        for h in history:
                            methods[h.method] += 1
                            if h.method == 'POST':
                                dash = h.json()
                                print("Post response: %s" % dash)
                                # assert len(dash['dashboard']['rows']) == 2
                        assert {'POST': 1, 'GET': 1} == methods

                    # check host and the service are tagged grafana and have the id
                    host_db = current_app.data.driver.db['host']
                    host002 = host_db.find_one({'_id': ObjectId(self.host_srv002['_id'])})
                    assert host002['ls_grafana']
                    assert host002['ls_grafana_panelid'] == 1
                    service_db = current_app.data.driver.db['service']
                    srv002 = service_db.find_one({'_id': ObjectId(self.host_srv002_srv['_id'])})
                    print("Service: %s" % srv002)
                    assert srv002['ls_grafana']
                    assert srv002['ls_grafana_panelid'] == 2

    def test_grafana_connection_error(self):
        """
        This test the connection error of grafana

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        # Create grafana in realm All + subrealm
        data = {
            'name': 'grafana All',
            'address': '192.168.0.101',
            'apikey': 'xxxxxxxxxxxx1',
            '_realm': self.realm_all,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/grafana', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        data['name'] = 'grafana 2'
        data['address'] = '192.168.0.102'
        response = requests.post(self.endpoint + '/grafana', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # force request of cron_grafana in the backend
        response = requests.get(self.endpoint + '/cron_grafana')
        resp = response.json()
        assert len(resp) == 2
        assert not resp['grafana All']['connection']
        assert not resp['grafana 2']['connection']

        myfile = open("/tmp/alignak_backend.log")
        lines = myfile.readlines()
        for line in lines:
            print("- %s" % line)
        assert 'Connection error to grafana grafana All' in lines[-5]
        assert '[cron_grafana] grafana All has no connection' in lines[-4]
        assert 'Connection error to grafana grafana 2' in lines[-3]
        assert '[cron_grafana] grafana 2 has no connection' in lines[-2]

    def test_cron_grafana_service(self):
        """
        This test the grafana cron in the cases:
         * a host has a new service
         * a host does not have ls_perf_data

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        # Create grafana in realm All + subrealm
        data = {
            'name': 'grafana All',
            'address': '192.168.0.101',
            'apikey': 'xxxxxxxxxxxx1',
            '_realm': self.realm_all,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/grafana', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        grafana_all = resp['_id']

        # Create a graphite in All B linked to grafana
        data = {
            'name': 'graphite All',
            'carbon_address': '192.168.0.101',
            'graphite_address': '192.168.0.101',
            'prefix': '',
            'grafana': grafana_all,
            '_realm': self.realm_all,
            '_sub_realm': False
        }
        response = requests.post(self.endpoint + '/graphite', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # add host 3, without ls_perf_data
        response = requests.get(self.endpoint + '/command', auth=self.auth)
        resp = response.json()
        rc = resp['_items']

        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[0]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = self.realm_all
        data['_sub_realm'] = False
        data['ls_last_check'] = int(time.time())
        data['name'] = 'srv003'
        response = requests.post(self.endpoint + '/host', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual(resp['_status'], 'OK')
        response = requests.get(self.endpoint + '/host/' + resp['_id'], auth=self.auth)
        host_srv003 = response.json()

        # Add a service for srv003
        data = json.loads(open('cfg/service_srv001_ping.json').read())
        data['host'] = host_srv003
        data['check_command'] = rc[0]['_id']
        data['_realm'] = self.realm_all
        data['_sub_realm'] = False
        data['name'] = 'load'
        data['ls_last_check'] = int(time.time())
        data['ls_perf_data'] = "load1=0.360;15.000;30.000;0; load5=0.420;10.000;25.000;0; " \
                               "load15=0.340;5.000;20.000;0;"
        response = requests.post(self.endpoint + '/service', json=data,
                                 headers=headers, auth=self.auth)

        from alignak_backend.app import app, cron_grafana
        with app.app_context():
            with requests_mock.mock() as mockreq:
                ret = [{"id": 1, "orgId": 1, "name": 'alignak-graphite-graphite B',
                        "type": "grafana-simple-json-datasource",
                        "typeLogoUrl": "public/plugins/grafana-simple-json-datasource/src/img/"
                                       "simpleJson_logo.svg",
                        "access": "proxy", "url": "http://127.0.0.1/glpi090/apirest.php",
                        "password": "", "user": "", "database": "", "basicAuth": True,
                        "basicAuthUser": "", "basicAuthPassword": "", "withCredentials": False,
                        "isDefault": False}]
                mockreq.get('http://192.168.0.101:3000/api/datasources', json=ret)
                mockreq.post('http://192.168.0.101:3000/api/datasources',
                             json={'id': randint(2, 10)})
                mockreq.post('http://192.168.0.101:3000/api/dashboards/db', json='true')

                dashboards = json.loads(cron_grafana(engine='jsondumps'))
                # Created a dashboard for the host srv001 (it has perf_data in the host check)
                assert len(dashboards['grafana All']['created_dashboards']) == 1
                assert dashboards['grafana All']['created_dashboards'][0] == 'srv001'
                # Did not created a dashboard for the host srv003:
                # - no perf_data in the host check!
                # - no service with perf_data!
                # assert len(dashboards['grafana All']['create_dashboard']) == 2
                # assert dashboards['grafana All']['created_dashboards'][1] == 'srv003'

            # add a service with no perf_data in host 3
            data = json.loads(open('cfg/service_srv001_ping.json').read())
            data['host'] = host_srv003['_id']
            data['check_command'] = rc[0]['_id']
            data['_realm'] = self.realm_all
            data['name'] = 'srv1'
            data['ls_last_check'] = int(time.time())
            data['ls_perf_data'] = ""
            requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)

            # add a service with no check execution time in host 3
            data = json.loads(open('cfg/service_srv001_ping.json').read())
            data['host'] = host_srv003['_id']
            data['check_command'] = rc[0]['_id']
            data['_realm'] = self.realm_all
            data['name'] = 'srv2'
            data['ls_last_check'] = 0
            data['ls_perf_data'] = "load1=0.360;15.000;30.000;0; load5=0.420;10.000;25.000;0; " \
                                   "load15=0.340;5.000;20.000;0;"
            requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)

            # add a service with perf_data and execution time in host 3
            data = json.loads(open('cfg/service_srv001_ping.json').read())
            data['host'] = host_srv003['_id']
            data['check_command'] = rc[0]['_id']
            data['_realm'] = self.realm_all
            data['name'] = 'load'
            data['ls_last_check'] = int(time.time())
            data['ls_perf_data'] = "load1=0.360;15.000;30.000;0; load5=0.420;10.000;25.000;0; " \
                                   "load15=0.340;5.000;20.000;0;"
            requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)

            with requests_mock.mock() as mockreq:
                ret = [{"id": 1, "orgId": 1, "name": 'alignak-graphite-graphite B',
                        "type": "grafana-simple-json-datasource",
                        "typeLogoUrl": "public/plugins/grafana-simple-json-datasource/src/img/"
                                       "simpleJson_logo.svg",
                        "access": "proxy", "url": "http://127.0.0.1/glpi090/apirest.php",
                        "password": "", "user": "", "database": "", "basicAuth": True,
                        "basicAuthUser": "", "basicAuthPassword": "", "withCredentials": False,
                        "isDefault": False}]
                mockreq.get('http://192.168.0.101:3000/api/datasources', json=ret)
                mockreq.post('http://192.168.0.101:3000/api/datasources',
                             json={'id': randint(2, 10)})
                mockreq.post('http://192.168.0.101:3000/api/dashboards/db', json='true')

                dashboards = json.loads(cron_grafana(engine='jsondumps'))
                assert len(dashboards['grafana All']['created_dashboards']) == 1
                # Created a dashboard including the service
                assert dashboards['grafana All']['created_dashboards'][0] == 'srv003/load'
                # Did not created a dashboard for any other services!
