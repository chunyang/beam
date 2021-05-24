#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Dataflow credentials and authentication."""

# pytype: skip-file

import logging
import socket
import threading

import google.auth

from apache_beam import version

# When we are running in GCE, we can authenticate with VM credentials.
is_running_in_gce = False

# When we are running in GCE, this value is set based on worker startup
# information.
executing_project = None

_LOGGER = logging.getLogger(__name__)


def get_user_agent():
  """For internal use only; no backwards-compatibility guarantees.

  Returns:
    A str representing the Beam Python SDK.
  """
  return f"beam-python-sdk/{version.__version__}"


def set_running_in_gce(worker_executing_project):
  """For internal use only; no backwards-compatibility guarantees.

  Informs the authentication library that we are running in GCE.

  When we are running in GCE, we have the option of using the VM metadata
  credentials for authentication to Google services.

  Args:
    worker_executing_project: The project running the workflow. This information
      comes from worker startup information.
  """
  global is_running_in_gce
  global executing_project
  is_running_in_gce = True
  executing_project = worker_executing_project


def get_service_credentials():
  """For internal use only; no backwards-compatibility guarantees.

  Get credentials to access Google services.

  Returns:
    A ``google.auth.credentials.Credentials`` object or None if credentials
    not found. Returned object is thread-safe.
  """
  return _Credentials.get_service_credentials()


class _Credentials(object):
  _credentials_lock = threading.Lock()
  _credentials_init = False
  _credentials = None

  @classmethod
  def get_service_credentials(cls):
    if cls._credentials_init:
      return cls._credentials

    with cls._credentials_lock:
      if cls._credentials_init:
        return cls._credentials

      # apitools use urllib with the global timeout. Set it to 60 seconds
      # to prevent network related stuckness issues.
      if not socket.getdefaulttimeout():
        _LOGGER.info("Setting socket default timeout to 60 seconds.")
        socket.setdefaulttimeout(60)
      _LOGGER.info(
          "socket default timeout is %s seconds.", socket.getdefaulttimeout())

      cls._credentials = cls._get_service_credentials()
      cls._credentials_init = True

    return cls._credentials

  @staticmethod
  def _get_service_credentials():
    client_scopes = [
        'https://www.googleapis.com/auth/bigquery',
        'https://www.googleapis.com/auth/cloud-platform',
        'https://www.googleapis.com/auth/devstorage.full_control',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/datastore',
        'https://www.googleapis.com/auth/spanner.admin',
        'https://www.googleapis.com/auth/spanner.data'
    ]
    try:
      credentials = google.auth.default(scopes=client_scopes)
      logging.debug(
          'Connecting using Google Application Default '
          'Credentials.')
      return credentials
    except Exception as e:
      _LOGGER.warning(
          'Unable to find default credentials to use: %s\n'
          'Connecting anonymously.',
          e)
      return None
