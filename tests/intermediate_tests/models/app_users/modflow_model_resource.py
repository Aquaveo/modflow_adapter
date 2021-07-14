"""
********************************************************************************
* Name: gssha_model_resource
* Author: ckrewson
* Created On: July 31, 2018
* Copyright: (c) Aquaveo 2018
********************************************************************************
"""
import datetime
import unittest
from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import Session

from tethysext.atcore.models.app_users import AppUsersBase
from modflow_adapter.models.app_users.modflow_model_resource import ModflowModelResource


from tests import TEST_DB_URL


def setUpModule():
    global transaction, connection, engine

    # Connect to the database and create the schema within a transaction
    engine = create_engine(TEST_DB_URL)
    connection = engine.connect()
    transaction = connection.begin()

    AppUsersBase.metadata.create_all(connection)
    # If you want to insert fixtures to the DB, do it here


def tearDownModule():
    # Roll back the top level transaction and disconnect from the database
    transaction.rollback()
    connection.close()
    engine.dispose()


class ModflowModelResourceTests(unittest.TestCase):

    def setUp(self):
        self.transaction = connection.begin_nested()
        self.session = Session(connection)

        self.name = "test_organization"
        self.description = "Bad Description"
        self.created_by = "foo"
        self.creation_date = datetime.datetime.utcnow()

    def tearDown(self):
        self.session.close()
        self.transaction.rollback()

    def test_create_modflow_model_resource(self):
        resource = ModflowModelResource(
            name=self.name,
            description=self.description,
            created_by=self.created_by,
            date_created=self.creation_date,
        )

        self.session.add(resource)
        self.session.commit()

        all_resources_count = self.session.query(ModflowModelResource).count()
        all_resources = self.session.query(ModflowModelResource).all()

        self.assertEqual(all_resources_count, 1)

        for resource in all_resources:
            self.assertEqual(resource.name, self.name)
            self.assertEqual(resource.description, self.description)
            self.assertEqual(resource.created_by, self.created_by)
            self.assertEqual(resource.date_created, self.creation_date)
            self.assertEqual(resource.type, ModflowModelResource.TYPE)
            self.assertEqual(resource.DISPLAY_TYPE_SINGULAR, ModflowModelResource.DISPLAY_TYPE_SINGULAR)
            self.assertEqual(resource.DISPLAY_TYPE_PLURAL, ModflowModelResource.DISPLAY_TYPE_PLURAL)
