from tests.unit_tests import *  # noqa: F401, F403
import os
# NOTE: database user given must be a superuser to successfully execute all tests.
default_connection = 'postgresql://tethys_super:pass@172.17.0.1:5435/modflow_test'
TEST_DB_URL = os.environ.get('MODFLOW_TEST_DATABASE', default_connection)  # noqa: F401, F403
