"""
********************************************************************************
* Name: modflow_spatial_manager
* Author: ckrewson
* Created On: July 09, 2018
* Copyright: (c) Aquaveo 2018
********************************************************************************
"""
import os
import json
import mock
import unittest
import warnings

from modflow_adapter.services.modflow_spatial_manager import ModflowSpatialManager


class ModflowSpatialManagerTests(unittest.TestCase):

    def setUp(self):
        self.geoserver_engine = mock.MagicMock()
        self.store_name = '123_456_789'
        self.store_name_dashes = self.store_name.replace('_', '-')
        self.mock_model_file_db = mock.MagicMock()
        self.modflow_version = 'mf2005'
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.test_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.test_files = os.path.join(self.test_dir, 'files', 'modflow_spatial_manager', 'test_with_results')
        self.mock_model_file_db.db_dir = self.test_files
        self.mock_model_file_db.get_id.return_value = self.store_name
        self.mock_model_file_db.list.return_value = os.listdir(self.test_files)
        warnings.simplefilter("ignore", ResourceWarning)

    def tearDown(self):
        pass

    def test_load_model(self):
        self.msm.load_model()
        self.assertIsNotNone(self.msm.flopy_model)

    def test_load_model_no_nam(self):
        self.mock_model_file_db.list.return_value = ['FAKE.oc']
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.assertRaises(OSError, self.msm.load_model)
        self.assertIsNone(self.msm.flopy_model)

    def test_load_model_no_exe(self):
        self.modflow_version = 'fake'
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )

        self.assertRaises(OSError, self.msm.load_model)
        self.assertIsNone(self.msm.flopy_model)

    def test_get_unique_item_name(self):
        item_name = 'foo'
        ret = self.msm.get_unique_item_name(item_name=item_name)
        self.assertEqual(ret, '{}'.format(item_name))

    def test_get_unique_item_name_with_model_file_db(self):
        item_name = 'foo'
        ret = self.msm.get_unique_item_name(item_name=item_name, model_file_db=self.mock_model_file_db)
        self.assertEqual(ret, '{}_{}'.format(self.store_name_dashes, item_name))

    def test_get_unique_item_name_with_scenario_id(self):
        item_name = 'foo'
        scenario_id = 'bar'
        ret = self.msm.get_unique_item_name(item_name=item_name, scenario_id=scenario_id)
        self.assertEqual(ret, '{}_{}'.format(scenario_id, item_name))

    def test_get_unique_item_name_with_variable(self):
        item_name = 'foo'
        variable = 'bar'
        ret = self.msm.get_unique_item_name(item_name=item_name, variable=variable)
        self.assertEqual(ret, '{}_{}'.format(item_name, variable))

    def test_get_unique_item_name_with_suffix(self):
        item_name = 'foo'
        suffix = 'bar'
        ret = self.msm.get_unique_item_name(item_name=item_name, suffix=suffix)
        self.assertEqual(ret, '{}_{}'.format(item_name, suffix))

    def test_get_unique_item_name_with_workspace(self):
        item_name = 'foo'
        ret = self.msm.get_unique_item_name(item_name=item_name, with_workspace=True)
        self.assertEqual(ret, '{}:{}'.format('modflow', item_name))

    def test_get_extent_for_project(self):
        mock_attrs = json.dumps({'model_extents': json.dumps([1, 1, 1, 1]), 'database_id': 1234})
        mock_resource = mock.MagicMock(_attributes=mock_attrs)
        self.msm.model_file_db._app.get_persistent_store_database()().query().all.return_value = [mock_resource]
        self.msm.model_file_db.get_id.return_value = 1234
        ret = self.msm.get_extent_for_project(self.msm.model_file_db)
        self.assertEqual(ret, [1.0, 1.0, 1.0, 1.0])

    def test_get_extent_for_project_model_not_loaded(self):
        self.msm.map_extents = [0, 0, 19, 0]
        ret = self.msm.get_extent_for_project(self.msm.model_file_db)
        self.assertEqual(ret, [0, 0, 19, 0])

    def test_get_projection_string(self):
        self.msm.load_model()
        self.msm.flopy_model.sr.epsg = 3587
        ret = self.msm.get_projection_string()
        self.assertEqual(ret, '+proj=lcc +lat_1=45.7 +lat_2=44.18333333333333 +lat_0=43.31666666666667 +lon'
                              '_0=-84.36666666666666 +x_0=6000000 +y_0=0 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0'
                              ' +units=m +no_defs ')

    def test_get_projection_string_model_not_loaded(self):
        ret = self.msm.get_projection_string()
        self.assertIsNone(ret)

    def test_get_projection_units(self):
        self.msm.load_model()
        self.msm.flopy_model.sr.units = 'meters'
        ret = self.msm.get_projection_units()
        self.assertEqual(ret, 'meters')

    def test_get_projection_units_model_not_loaded(self):
        ret = self.msm.get_projection_units()
        self.assertEqual(ret, 'meters')

    def test_modify_spatial_reference(self):
        ret = self.msm.modify_spatial_reference()
        self.assertIsNone(ret.epsg)

    def test_get_head_data_hds_file(self):
        ret = self.msm.get_head_data()
        self.assertIsNotNone(ret)

    def test_get_head_data_no_hds_file(self):
        self.test_files = os.path.join(self.test_dir, 'files', 'modflow_spatial_manager', 'test_without_results')
        self.mock_model_file_db.directory = self.test_files
        self.mock_model_file_db.list.return_value = os.listdir(self.test_files)
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        ret = self.msm.get_head_data()
        self.assertIsNone(ret)

    def test_get_package_layer_attribute_info(self):
        ret = self.msm.get_package_layer_attribute_info()
        self.assertIsInstance(ret, dict)
        result = {'BAS6': {'strt_001': {'maximum': 45.0, 'minimum': 11.4}}}
        self.assertEqual(ret['BAS6']['strt_001']['maximum'], result['BAS6']['strt_001']['maximum'])

    def test_get_head_info(self):
        ret = self.msm.get_head_info()
        self.assertIsInstance(ret, dict)
        result = {'1': {'minimum': 10.537197, 'maximum': 999.0}}
        self.assertEqual(ret['1']['maximum'], result['1']['maximum'])

    def test_get_head_info_no_hds(self):
        self.test_files = os.path.join(self.test_dir, 'files', 'modflow_spatial_manager', 'test_without_results')
        self.mock_model_file_db.directory = self.test_files
        self.mock_model_file_db.list.return_value = os.listdir(self.test_files)
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        ret = self.msm.get_head_info()
        self.assertIsNone(ret)

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    @mock.patch('flopy.utils.reference.getprj')
    def test_create_model_boundary_layer_no_layer_group(self, mock_prj,  _):
        self.msm.gs_engine.get_layer_group.return_value = {'success': False,
                                                           'result': {}
                                                           }
        mock_prj.return_value = 'fake prj'
        self.msm.gs_engine._process_identifier.return_value = ['modflow', 'test']
        self.msm.gs_engine._get_geoserver_catalog_object.get_resource.return_value = mock.MagicMock(
            latlon_bbox=[1.0, 1.0, 1.0, 1.0]
        )
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.msm.create_model_boundary_layer()
        geoserver_store = "{}:{}_{}".format(self.msm.WORKSPACE, self.store_name_dashes, self.msm.VL_MODEL_BOUNDARY)
        temp_name = "{}_{}".format(self.store_name_dashes, self.msm.VL_MODEL_BOUNDARY)
        temp_zip = "{}.zip".format(temp_name)
        temp_prj = "{}.prj".format(temp_name)
        temp_shp = "{}.shp".format(temp_name)

        shapefile_call_args = self.msm.gs_engine.create_shapefile_resource.call_args_list
        self.assertEqual(geoserver_store, shapefile_call_args[0][0][0])
        self.assertEqual(temp_zip, shapefile_call_args[0][1]['shapefile_zip'])
        self.msm.gs_engine.create_shapefile_resource.assert_called()

        style_call_args = self.msm.gs_engine.update_layer.call_args_list
        self.assertEqual(geoserver_store, style_call_args[0][1]['layer_id'])
        self.assertEqual(self.msm.VL_MODEL_BOUNDARY, style_call_args[0][1]['default_style'])

        self.assertFalse(os.path.isfile(temp_shp))
        self.assertFalse(os.path.isfile(temp_prj))
        self.assertFalse(os.path.isfile(temp_zip))

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    @mock.patch('flopy.utils.reference.getprj')
    def test_create_model_boundary_layer_ex_layer_group(self, mock_prj, _):
        self.msm.gs_engine.get_layer_group.return_value = {'success': True,
                                                           'result': {'layers': ['ex_layer'],
                                                                      'styles': ['ex_style']
                                                                      }
                                                           }
        mock_prj.return_value = 'fake prj'
        self.msm.get_unique_item_name = mock.MagicMock()
        self.msm.get_unique_item_name.side_effect = ['new_layer', 'new_style']
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.msm.create_model_boundary_layer()
        shapefile_call_args = self.msm.gs_engine.create_shapefile_resource.call_args_list
        geoserver_store = "{}:{}_{}".format(self.msm.WORKSPACE, self.store_name_dashes, self.msm.VL_MODEL_BOUNDARY)
        temp_name = "{}_{}".format(self.store_name_dashes, self.msm.VL_MODEL_BOUNDARY)
        temp_zip = "{}.zip".format(temp_name)
        temp_prj = "{}.prj".format(temp_name)
        temp_shp = "{}.shp".format(temp_name)
        self.assertEqual(geoserver_store, shapefile_call_args[0][0][0])
        self.assertEqual(temp_zip, shapefile_call_args[0][1]['shapefile_zip'])
        self.msm.gs_engine.create_shapefile_resource.assert_called()

        style_call_args = self.msm.gs_engine.update_layer.call_args_list
        self.assertEqual(geoserver_store, style_call_args[0][1]['layer_id'])
        self.assertEqual(self.msm.VL_MODEL_BOUNDARY, style_call_args[0][1]['default_style'])

        layer_group_call_args = self.msm.gs_engine.update_layer_group.call_args_list
        self.assertEqual("{}:{}".format(self.msm.WORKSPACE, self.msm.VL_MODEL_BOUNDARY),
                         layer_group_call_args[0][1]['layer_group_id'])
        self.assertEqual(2, len(layer_group_call_args[0][1]['layers']))
        self.assertEqual(2, len(layer_group_call_args[0][1]['styles']))

        self.assertFalse(os.path.isfile(temp_shp))
        self.assertFalse(os.path.isfile(temp_prj))
        self.assertFalse(os.path.isfile(temp_zip))

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    def test_delete_model_boundary_layer(self, _):
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.msm.delete_model_boundary_layer()
        self.msm.gs_engine.delete_resource.assert_called()
        call_args = self.msm.gs_engine.delete_resource.call_args_list
        geoserver_store = "{}:{}_{}".format(self.msm.WORKSPACE, self.store_name_dashes, self.msm.VL_MODEL_BOUNDARY)
        self.assertEqual(geoserver_store, call_args[0][0][0])

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    @mock.patch('flopy.utils.reference.getprj')
    def test_create_package_shapefile_layers(self, mock_prj,  _):
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        mock_prj.return_value = 'fake prj'
        self.msm.map_extents = [0, 0, 0, 0]
        self.msm.create_package_shapefile_layers()
        self.msm.gs_engine.create_coverage_resource.assert_called()
        shapefile_call_args = self.msm.gs_engine.create_coverage_resource.call_args_list
        geoserver_store = "{}:{}_{}".format(self.msm.WORKSPACE, self.store_name_dashes, "DIS")
        temp_name = "{}_{}-{}".format(self.store_name_dashes, "DIS", "thickn_001")
        temp_shp = "{}.zip".format(temp_name)
        self.assertEqual("{}-thickn_001".format(geoserver_store), shapefile_call_args[0][0][0])
        self.assertEqual(temp_shp, shapefile_call_args[0][1]['coverage_file'])
        self.assertEqual('geotiff', shapefile_call_args[0][1]['coverage_type'])
        self.msm.gs_engine.create_coverage_resource.assert_called()

        style_call_args = self.msm.gs_engine.update_layer.call_args_list
        self.assertEqual("{}-thickn_001".format(geoserver_store), style_call_args[0][1]['layer_id'])
        self.assertEqual("{}_{}".format(self.msm.WORKSPACE, self.msm.RL), style_call_args[0][1]['default_style'])

        self.assertFalse(os.path.isfile(temp_shp))

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    def test_delete_package_shapefile_layers(self, _):
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.msm.delete_package_shapefile_layers()
        self.msm.gs_engine.delete_resource.assert_called()
        call_args = self.msm.gs_engine.delete_resource.call_args_list
        geoserver_store = "{}:{}_{}-{}".format(self.msm.WORKSPACE, self.store_name_dashes, "DIS", "thickn_001")
        self.assertEqual(geoserver_store, call_args[0][0][0])

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    def test_create_raster_style(self, _):
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.msm.create_raster_style()
        self.msm.gs_api.create_style.assert_called()

        call_args = self.msm.gs_api.create_style.call_args_list
        self.assertIn(self.msm.WORKSPACE, call_args[0][1]['workspace'])
        self.assertEqual("{}_{}".format(self.msm.WORKSPACE, self.msm.RL), call_args[0][1]['style_name'])
        self.assertEqual(os.path.join(self.msm.SLD_PATH, self.msm.RL + '.sld'),
                         call_args[0][1]['sld_template'])
        self.assertEqual({}, call_args[0][1]['sld_context'])
        self.assertEqual(True, call_args[0][1]['overwrite'])

        self.msm.gs_api.reload.assert_called_once()

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    def test_delete_raster_style(self, _):
        msm = ModflowSpatialManager(self.geoserver_engine,
                                    self.mock_model_file_db,
                                    self.modflow_version,
                                    )
        msm.delete_raster_style(purge=True, reload_config=True)
        call_args = msm.gs_api.delete_style.call_args_list
        self.assertIn(self.msm.WORKSPACE, call_args[0][1]['workspace'])
        self.assertEqual("{}_{}".format(self.msm.WORKSPACE, self.msm.RL), call_args[0][1]['style_name'])
        self.assertEqual(True, call_args[0][1]['purge'])
        msm.gs_api.reload.assert_called_once()

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    def test_create_head_raster_layer_no_hds_file(self, _):
        self.test_files = os.path.join(self.test_dir, 'files', 'modflow_spatial_manager', 'test_without_results')
        self.mock_model_file_db.directory = self.test_files
        self.mock_model_file_db.list.return_value = os.listdir(self.test_files)
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.assertRaises(OSError, self.msm.create_head_raster_layer)

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    @mock.patch('flopy.utils.reference.getprj')
    def test_create_head_raster_layer_hds_file(self, mock_prj, _):
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        mock_prj.return_value = 'fake prj'
        self.msm.create_head_raster_layer()
        self.msm.gs_engine.create_coverage_resource.assert_called()
        shapefile_call_args = self.msm.gs_engine.create_coverage_resource.call_args_list
        geoserver_store = "{}:{}_{}_{}".format(self.msm.WORKSPACE, self.store_name_dashes, self.msm.RL_HEAD, '001')
        layer_name = "{}_{}_{}".format(self.store_name_dashes, self.msm.RL_HEAD, '001')
        tmp_zip = "{}.zip".format(layer_name)
        self.assertEqual(geoserver_store, shapefile_call_args[0][0][0])
        self.assertEqual(tmp_zip, shapefile_call_args[0][1]['coverage_file'])
        self.assertEqual('geotiff', shapefile_call_args[0][1]['coverage_type'])
        self.msm.gs_engine.create_coverage_resource.assert_called()

        style_call_args = self.msm.gs_engine.update_layer.call_args_list
        self.assertEqual(geoserver_store, style_call_args[0][1]['layer_id'])
        self.assertEqual("{}_{}".format(self.msm.WORKSPACE, self.msm.RL), style_call_args[0][1]['default_style'])

        self.assertFalse(os.path.isfile(tmp_zip))

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    def test_delete_head_raster_layer_no_hds_file(self, _):
        self.test_files = os.path.join(self.test_dir, 'files', 'modflow_spatial_manager', 'test_without_results')
        self.mock_model_file_db.directory = self.test_files
        self.mock_model_file_db.list.return_value = os.listdir(self.test_files)
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.assertRaises(OSError, self.msm.delete_head_raster_layer)

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    def test_delete_head_raster_layer_hds_file(self, _):
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.msm.delete_head_raster_layer()
        self.msm.gs_engine.delete_resource.assert_called()
        call_args = self.msm.gs_engine.delete_resource.call_args_list
        geoserver_store = "{}:{}_{}_layer1".format(self.msm.WORKSPACE, self.store_name_dashes, self.msm.RL_HEAD)
        self.assertEqual(geoserver_store, call_args[0][0][0])

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    def test_create_head_contour_layer_no_hds_file(self, _):
        self.test_files = os.path.join(self.test_dir, 'files', 'modflow_spatial_manager', 'test_without_results')
        self.mock_model_file_db.directory = self.test_files
        self.mock_model_file_db.list.return_value = os.listdir(self.test_files)
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.assertRaises(OSError, self.msm.create_head_contour_layer)

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    def test_create_head_contour_layer_hds_file(self, _):
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.msm.load_model()
        self.msm.flopy_model.sr.epsg = 2901
        self.msm.create_head_contour_layer()
        self.msm.gs_engine.create_shapefile_resource.assert_called()
        shapefile_call_args = self.msm.gs_engine.create_shapefile_resource.call_args_list
        geoserver_store = "{}:{}_{}_{}".format(self.msm.WORKSPACE,
                                               self.store_name_dashes,
                                               self.msm.VL_HEAD_CONTOUR, '001')
        temp_shp = "{}_{}_{}".format(self.store_name_dashes,
                                     self.msm.VL_HEAD_CONTOUR, '001')
        self.assertEqual(geoserver_store, shapefile_call_args[0][0][0])
        self.assertEqual(temp_shp, shapefile_call_args[0][1]['shapefile_base'])

        style_call_args = self.msm.gs_engine.update_layer.call_args_list
        self.assertEqual(geoserver_store, style_call_args[0][1]['layer_id'])
        self.assertEqual(self.msm.VL_HEAD_CONTOUR, style_call_args[0][1]['default_style'])

        self.assertFalse(os.path.isfile(temp_shp))

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    def test_delete_head_contour_layer_no_hds_file(self, _):
        self.test_files = os.path.join(self.test_dir, 'files', 'modflow_spatial_manager', 'test_without_results')
        self.mock_model_file_db.directory = self.test_files
        self.mock_model_file_db.list.return_value = os.listdir(self.test_files)
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.assertRaises(OSError, self.msm.delete_head_contour_layer)

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    def test_delete_head_contour_layer_hds_file(self, _):
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.msm.delete_head_contour_layer()
        self.msm.gs_engine.delete_resource.assert_called()
        call_args = self.msm.gs_engine.delete_resource.call_args_list
        geoserver_store = "{}:{}_{}_layer1".format(self.msm.WORKSPACE, self.store_name_dashes, self.msm.VL_HEAD_CONTOUR)
        self.assertEqual(geoserver_store, call_args[0][0][0])

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    def test_create_all_vector_layers(self, _):
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.msm.load_model()
        self.msm.flopy_model.sr.epsg = 2901
        self.msm.create_all_vector_layers()

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    def test_delete_all_vector_layers(self, _):
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.msm.delete_all_vector_layers()

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    @mock.patch('flopy.utils.reference.getprj')
    def test_create_all_raster_layers(self, mock_prj, _):
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        mock_prj.return_value = 'fake prj'
        self.msm.create_all_raster_layers()
        self.msm.gs_engine.create_coverage_resource.assert_called()

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    def test_delete_all_raster_layers(self, _):
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.msm.delete_all_raster_layers()
        self.msm.gs_engine.delete_resource.assert_called()

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    @mock.patch('flopy.utils.reference.getprj')
    def test_create_all_layers(self, mock_prj, _):
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        mock_prj.return_value = 'fake prj'
        self.msm.create_all_layers()
        self.msm.gs_engine.create_coverage_resource.assert_called()

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    def test_delete_all_layers(self, _):
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.msm.delete_all_layers()
        self.msm.gs_engine.delete_resource.assert_called()

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    def test_create_all_styles(self, _):
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.msm.create_all_styles()

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    def test_delete_all_styles(self, _):
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.msm.delete_all_styles()

    @mock.patch('tethysext.atcore.services.base_spatial_manager.GeoServerAPI')
    def test_create_all(self, _):
        self.msm = ModflowSpatialManager(self.geoserver_engine,
                                         self.mock_model_file_db,
                                         self.modflow_version,
                                         )
        self.msm.load_model()
        self.msm.flopy_model.sr.epsg = 2901
        self.msm.create_all()
        self.msm.gs_engine.create_coverage_resource.assert_called()
        self.msm.gs_engine.create_shapefile_resource.assert_called()
