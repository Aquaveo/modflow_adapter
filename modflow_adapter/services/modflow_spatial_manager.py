"""
********************************************************************************
* Name: modflow_spatial_manager
* Author: ckrewson and mlebaron
* Created On: November 7, 2018
* Copyright: (c) Aquaveo 2018
********************************************************************************
"""
import os
import flopy
import zipfile
import fiona
import geopandas
import pandas
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy as np
import pyproj
import json
from flopy.utils.reference import SpatialReference
import flopy.utils.binaryfile as bf
from flopy.utils.util_array import Util2d, Util3d, Transient2d
from flopy.utils.util_list import MfList
from flopy.export.shapefile_utils import shape_attr_name
from shapely.geometry import mapping
from modflow_adapter.models.app_users.modflow_model_resource import ModflowModelResource

from tethysext.atcore.services.model_file_db_spatial_manager import ModelFileDBSpatialManager
from tethysext.atcore.services.base_spatial_manager import reload_config


class ModflowSpatialManager(ModelFileDBSpatialManager):
    """
    Managers GeoServer Layers for Modflow Projects.
    """
    WORKSPACE = 'modflow'
    URI = 'http://portal.aquaveo.com/modflow'
    BASE_SCENARIO_ID = 1
    EXE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'modflow_executables')
    SLD_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'sld_templates')

    # Vector Layer Types
    VL_HEAD_CONTOUR = 'head_contour'
    VL_MODEL_BOUNDARY = 'model_boundary'
    VL_MODEL_GRID = 'model_grid'
    VL_PACKAGE = 'package'

    # Raster Layer Types
    RL_HEAD = 'head_raster'
    RL_LOWBLUE = 'low_blue_raster'
    RL = 'raster'
    RL1 = 'raster_one_value'
    RLLB = 'raster_reverse'

    # Number of first stress periods to import
    MAX_STRESS_PERIOD = 5
    # STRESS_PERIOD_IMPORT = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60]
    STRESS_PERIOD_IMPORT = [0, 6, 7, 8, 12, 54, 55, 56, 60]

    # Layer Name Translation
    LAYER_GROUP_TRANSLATION_DICT = {
        'Model': 'Model',
        'Head': 'Simulated Head',
        'BAS': 'Layer Initial Setup (BAS)',
        'BAS6': 'Layer Initial Setup (BAS6)',
        'DIS': 'Layer Elevation (DIS)',
        'UPW': 'Aquifer Properties (UPW)',
        'SFR': 'Streamflow-Routing (SFR)',
        'EVT': 'Evapotranspiration (EVT)',
        'WEL': 'Well (WEL)',
        'RCH': 'Recharge (RCH)',
        'CHD': 'Specified Head (CHD)',
        'RIV': 'RIVER (RIV)',
    }

    # LOW IS BLUE RASTER TYPE
    LOW_BLUE_STYLE_PACKAGE = ['WEL', 'EVT']

    # If value is a list, first item is for negative and second is for positive values
    ATTRIBUTE_TRANSLATION_DICT = {
        'thickn-dis': "Thickness",
        'botm-dis': "Bottom",
        'model_top-dis': "Top Elevation",
        'ibound-bas6': 'Active Cells',
        'strt-bas6': 'Initial Starting Head',
        'hani-upw': 'Horizontal Anisotropy',
        'vani-upw': 'Vertical Anisotropy',
        'hani-lpf': 'Horizontal Anisotropy',
        'vani-lpf': 'Vertical Anisotropy',
        'hk-upw': 'Horizontal Hydraulic Conductivity',
        'hk-lfp': 'Horizontal Hydraulic Conductivity',
        'ss-upw': 'Storage Coefficient',
        'ss-lpf': 'Storage Coefficient',
        'sy-upw': 'Specific Yield',
        'sy-lpf': 'Specific Yield',
        'vka-upw': 'Vertical Hydraulic Conductivity',
        'vka-lpf': 'Vertical Hydraulic Conductivity',
        'vkcb-upw': 'Vertical Hydraulic Conductivity of Confining Bed Underneath',
        'vkcb-lpf': 'Vertical Hydraulic Conductivity of Confining Bed Underneath',
        'j-sfr': 'Column Number Containing Stream Reach',
        'iseg-sfr': 'Number of Stream Segment',
        'irea-sfr': 'Sequential Number in a Stream Segment of a Reach',
        'ireach-sfr': 'Sequential Number in a Stream Segment of a Reach',
        'rchl-sfr': 'Length of Channel within Model Cell',
        'strt-sfr': 'Top Elevation of Streambed',
        'slop-sfr': 'Stream Slope',
        'strh-sfr': 'Hydraulic Conductivity of the Streambed',
        'thts-sfr': 'Volumetric Water Content in the Unsaturated Zone',
        'thti-sfr': 'Initial Volumetric Water Content',
        'eps-sfr': 'Brooks-Corey Exponent',
        'uhc-sfr': 'Vertical Saturated Hydraulic Conductivity of the Unsaturated Zone',
        'flux-wel': ['Well Extraction Rates', 'Well Injection Rates'],
        # 'fluxneg-wel': 'Well Extraction Rates',
        # 'fluxpos-wel': 'Well Injection Rates',
        'evtr1-evt': 'Maximum Evapotranspiration Flux',
        'ievt1-evt': 'ET Removal Area',
        'etvr1-evt': 'Maximum Evapotranspiration Flux',
        'exdp1-evt': 'Evapotranspiration Extinction Depth',
        'surf1-evt': 'Elevation of the Evapotranspiration Surface',
        'rech-rch': 'Recharge',
        'shea-chd': 'Head at the start of Stress Period',
        'ehea-chd': 'Head at the end of Stress Period',
        'bhea-ghb': 'General Head on the boundary',
        'cond-ghb': 'Hydraulic Conductance of the interface between aquifer cell and the boundary',
        'ifact-ghb': 'Factor used to calculate hydraulic conductance from parameter value',
        'elev-drn': 'Drain Elevation',
        'cond-drn': 'Drain Conductance',
        'ifact-drn': 'Factor used to calculate hydraulic conductance from parameter value',
        'stag-riv': 'Head in the River',
        'cond-riv': 'Riverbed Hydraulic Conductance',
        'rbot-riv': 'Elevation of the bottom of the riverbed',
        'cell-riv': 'Cell number containing the river reach',
    }

    ATTRIBUTE_UNIT_DICT = {
        'thickn-dis': "#lenunit#",
        'botm-dis': "#lenunit#",
        'model_top-dis': "#lenunit#",
        'ibound-bas6': '',
        'strt-bas6': '#lenunit#',
        'hani-upw': '',
        'hani-lpf': '',
        'hk-upw': '#lenunit#/#timeunit#',
        'hk-lfp': '#lenunit#/#timeunit#',
        'ss-upw': '',
        'ss-lpf': '',
        'sy-upw': '',
        'sy-lpf': '',
        'vka-upw': '',
        'vka-lpf': '',
        'vkcb-upw': '#lenunit#/#timeunit#',
        'vkcb-lpf': '#lenunit#/#timeunit#',
        'j-sfr': '',
        'iseg-sfr': '',
        'irea-sfr': '',
        'rchl-sfr': '#lenunit#',
        'strt-sfr': '#lenunit#',
        'slop-sfr': '',
        'strh-sfr': '#lenunit#/#timeunit#',
        'thts-sfr': '#lenunit#^3',
        'thti-sfr': '#lenunit#^3',
        'eps-sfr': '',
        'uhc-sfr': '#lenunit#/#timeunit#',
        'flux-wel': '#lenunit#^3/#timeunit#',
        'evtr1-evt': '#lenunit#^3/#timeunit#',
        'ievt1-evt': '',
        'etvr1-evt': '#lenunit#^3/#timeunit#',
        'exdp1-evt': '#lenunit#',
        'surf1-evt': '#lenunit#',
        'rech-rch': '#lenunit#/#timeunit#',
        'shea-chd': '#lenunit#',
        'ehea-chd': '#lenunit#',
        'bhea-ghb': '#lenunit#',
        'cond-ghb': '#lenunit#^2/#timeunit#',
        'ifact-ghb': '',
        'elev-drn': '#lenunit#',
        'cond-drn': '#lenunit#^2/#timeunit#',
        'ifact-drn': '',
        'stag-riv': '#lenunit#',
        'cond-riv': '#lenunit#/#timeunit#',
        'rbot-riv': '#lenunit#',
        'cell-riv': '',
    }

    def __init__(self, geoserver_engine, model_file_db_connection, modflow_version):
        """
        Constructor

        Args:
            geoserver_engine(tethys_dataset_services.GeoServerEngine): Tethys geoserver engine.
            model_file_db_connection(ModelFileDatabaseConnection): Model File Database object
            modflow_version(Str): Version of Modflow executable (i.e. mf2005, mfnwt, etc
        """
        super().__init__(geoserver_engine)
        self.model_file_db = model_file_db_connection
        self.modflow_version = modflow_version
        self.flopy_model = None
        self.proj_file = None
        self.map_extents = None
        self.model_selection_bounds = None
        self._boundary = None

    def load_boundary(self):
        if not self._boundary:
            if not self.flopy_model:
                self.load_model()

            tmp_grid_name = 'temp_grid_file'
            tmp_grid_shapefile = "{}.shp".format(tmp_grid_name)

            # Open the gridded shapefile, select the values with Ibound not 0, and make a union from them
            gdf_boundary = []
            for layer in range(self.flopy_model.dis.nlay):
                print("number of layer is:" + str(self.flopy_model.dis.nlay))
                self.flopy_model.bas6.ibound[layer].export(tmp_grid_shapefile)
                gdf = geopandas.read_file(tmp_grid_shapefile)
                ibound_col = 'ibound__' + str(layer)
                if layer > 0:
                    gdf_boundary.append(gdf[gdf[ibound_col] != 0], sort=False)
                else:
                    gdf_boundary = gdf[gdf[ibound_col] != 0]
            self._boundary = gdf_boundary.geometry.unary_union

    @reload_config()
    def create_workspace(self, reload_config=True):
        """
        Create workspace.
        """
        self.gs_engine.create_workspace(self.WORKSPACE, self.URI)

        return True

    def load_model(self):
        """
        Loads MODFLOW model using flopy.
        """
        # Get correct modflow version executable
        model_exe = os.path.join(self.EXE_PATH, self.modflow_version)

        model_file_list = self.model_file_db.list()
        nam_file_path = None

        # Loop through model file database for a .nam or .mfn file
        for file in model_file_list:
            # TODO: figure out .mfn problems
            if file.split(".")[-1] in ['nam', 'mfn']:
                nam_file_path = os.path.join(self.model_file_db.db_dir, file)
                break

        if not nam_file_path:
            raise OSError("Nam file does not exist in the model file database")

        if not os.path.isfile(model_exe):
            raise OSError("{} does not exist".format(model_exe))

        # Load flopy_model from the model file database
        flopy_model = flopy.modflow.Modflow.load(
            file,
            model_ws=self.model_file_db.db_dir,
            verbose=False,
            check=True,
            exe_name=model_exe)

        # Change property from False to the model when loaded
        self.flopy_model = flopy_model

    def get_unique_item_name(self, item_name, variable='', suffix='', scenario_id=None, model_file_db=None,
                             with_workspace=False):
        """
        Construct the unique name for the specific item.

        Args:
            item_name(str): name of item.
            variable(str): Variable name.
            suffix(str): suffix to append to name (e.g.: 'labels').
            scenario_id(int): the id of the scenario.
            model_file_db(ModelFileDBConnection): Model File Database Connection Instance
            with_workspace(bool): include the workspace if True. Defaults to False.

        Returns:
            str: unique name for item.
        """
        # e.g.: <model_id>_<scenario_id>_<item_name>_<suffix>
        name_parts = []

        if model_file_db is not None:
            name_parts.append(self.model_file_db.get_id().replace('_', '-'))

        if scenario_id is not None:
            name_parts.append(str(scenario_id))

        name_parts.append(str(item_name))

        if variable:
            name_parts.append(variable)

        # e.g.: 88c1b4ce-7def-43fd-b19f-1fca8fea282d_model_boundary_legend
        if suffix:
            name_parts.append(suffix)

        name = '_'.join(name_parts)

        if with_workspace:
            return '{0}:{1}'.format(self.WORKSPACE, name)

        return name

    def get_number_layer(self):
        # Load flopy model if not already done
        if not self.flopy_model:
            self.load_model()

        number_layer = self.flopy_model.dis.nlay
        return number_layer

    def get_number_stress_period(self):
        # Load flopy model if not already done
        if not self.flopy_model:
            self.load_model()

        number_stress_period = self.flopy_model.dis.nper
        return number_stress_period

    def upload_all_layer_names_to_db(self, length_unit, time_unit):
        # Load flopy model if not already done
        if not self.flopy_model:
            self.load_model()

        geoserver_layer = {}
        geoserver_group = {}
        boundary_group = {}
        grid_group = {}
        head_group = {}
        package_group = {}

        boundary_layer = self.get_unique_item_name(
            item_name=self.VL_MODEL_BOUNDARY,
            model_file_db=self.model_file_db,
        )
        boundary_layer = "{}:{}-{}".format(self.WORKSPACE, self.WORKSPACE, boundary_layer)

        boundary_group[boundary_layer] = {'active': True, 'public_name': 'Boundary',
                                          'minimum': None, 'maximum': None}

        model_grid_layer = self.get_unique_item_name(
            item_name=self.VL_MODEL_GRID,
            model_file_db=self.model_file_db,
        )

        model_grid_layer = "{}:{}-{}".format(self.WORKSPACE, self.WORKSPACE, model_grid_layer)

        grid_group[model_grid_layer] = {'active': True, 'public_name': 'Model Grid',
                                        'minimum': None, 'maximum': None}

        geoserver_layer['Grid'] = grid_group
        geoserver_layer['Boundary'] = boundary_group
        geoserver_group['Model'] = {'active': True, 'public_name': self.LAYER_GROUP_TRANSLATION_DICT['Model']}

        head_info = self.get_head_info()
        if head_info is not None:
            for layer_number in head_info:
                layer_name = self.get_unique_item_name(
                    item_name=self.RL_HEAD,
                    model_file_db=self.model_file_db
                )

                # Create layer name based on modflow layer
                layer_name_number = '{}_{}'.format(layer_name, str(layer_number).zfill(3))
                public_layer_name = '{} in Layer {} ({})'.format('Head', layer_number, length_unit)
                geoserver_name = "modflow:modflow-{}".format(layer_name_number)
                maximum = head_info[layer_number]['maximum']
                minimum = head_info[layer_number]['minimum']
                head_group[geoserver_name] = {'active': True, 'public_name': public_layer_name,
                                              'minimum': str(minimum), 'maximum': str(maximum)}
            geoserver_layer['Head'] = head_group
            geoserver_group['Head'] = {'active': True, 'public_name': self.LAYER_GROUP_TRANSLATION_DICT['Head']}

        # Compose modflow package layers and create layers group for each modflow package
        for package in self.flopy_model.get_package_list():
            package_layer_info = self.get_package_layer_attribute_info()
            # Check package for data
            if package_layer_info[package]:
                package_group[package] = {}
                # loop through every available layer for each modflow package
                number_layer_attribute = 0
                for layer_attribute in package_layer_info[package]:
                    attribute = layer_attribute
                    maximum = package_layer_info[package][layer_attribute]['maximum']
                    minimum = package_layer_info[package][layer_attribute]['minimum']

                    if maximum != 0 or minimum != 0:
                        # Compose layer name
                        layer_name = self.get_unique_item_name(
                            item_name="{}-{}".format(package, attribute),
                            model_file_db=self.model_file_db,
                        )
                        new_layer_name, native_name, layer_unit, layer_number, stress_period = \
                            self.get_public_name(attribute, package, length_unit, time_unit)
                        # Special Case for Model Top Elevation

                        if attribute == 'model_top':
                            public_layer_name = "{} ({})".format(new_layer_name, length_unit.capitalize())
                        elif package == 'RCH' and self.flopy_model.dis.nper > 1:
                            public_layer_name = "{} in Stress Period {}".format('Recharge',
                                                                                int(attribute.split('_')[2]))
                        else:
                            if self.flopy_model.dis.nper > 1 and stress_period:
                                if layer_unit:
                                    public_layer_name = "{}({}) in Layer {} Stress Period {} ({})"\
                                        .format(new_layer_name, native_name, layer_number, stress_period, layer_unit)
                                else:
                                    public_layer_name = "{}({}) in Layer {} Stress Period {}"\
                                        .format(new_layer_name, native_name, layer_number, stress_period)
                            else:
                                if layer_unit:
                                    public_layer_name = "{}({}) in Layer {} ({})".format(new_layer_name, native_name,
                                                                                         layer_number, layer_unit)
                                else:
                                    public_layer_name = "{}({}) in Layer {}".format(new_layer_name, native_name,
                                                                                    layer_number)
                        geoserver_name = "modflow:modflow-{}".format(layer_name)
                        package_group[package][geoserver_name] = {'active': True,
                                                                  'public_name': public_layer_name,
                                                                  'minimum': str(minimum),
                                                                  'maximum': str(maximum)}
                        number_layer_attribute += 1
            if number_layer_attribute > 0:
                if package in self.LAYER_GROUP_TRANSLATION_DICT:
                    geoserver_group[package] = {'active': True,
                                                'public_name': self.LAYER_GROUP_TRANSLATION_DICT[package]}
                else:
                    geoserver_group[package] = {'active': True, 'public_name': package}

        geoserver_layer['Packages'] = package_group
        return geoserver_layer, geoserver_group

    def get_public_name(self, attribute_name, package, length_unit, time_unit):
        if "_" in attribute_name:
            # thickn_001
            # We have to do this to avoid the same initial for two package. For example strt in bas6 and strt in sfr
            layer_number = attribute_name.split('_')[1]
            if layer_number.isdigit():
                native_name = attribute_name.split('_')[0].lower()
            else:
                # handle special case such as model_top
                native_name = attribute_name

            layer_name, layer_unit = self.translate_layer_name(native_name + "-" + str(package).lower(), length_unit,
                                                               time_unit)
            layer_number = self.convert_to_int(layer_number)
            stress_period = ''
        else:
            # iseg001001
            # For some reason, well has different pattern!
            stress_period = self.convert_to_int(attribute_name[-3:])
            layer_number = self.convert_to_int(attribute_name[-6:-3])
            native_name = attribute_name[:-6].lower()
            layer_name, layer_unit = self.translate_layer_name(native_name + "-" + str(package).lower(), length_unit,
                                                               time_unit)
        if 'customtagpos' in native_name:
            native_name = native_name.replace('customtagpos', '')
        if 'customtagneg' in native_name:
            native_name = native_name.replace('customtagneg', '')
        native_name = native_name.upper()
        return layer_name, native_name, layer_unit, layer_number, stress_period

    @staticmethod
    def convert_to_int(string_data):
        if string_data.isdigit():
            string_data = int(string_data)
        return string_data

    def translate_layer_name(self, layer_name, length_unit, time_unit):
        org_layer_name = layer_name
        layer_unit = ''
        if 'customtagpos' in layer_name:
            layer_name = layer_name.replace('customtagpos', '')
            if layer_name in self.ATTRIBUTE_TRANSLATION_DICT:
                layer_name = self.ATTRIBUTE_TRANSLATION_DICT[layer_name][1]
        if 'customtagneg' in layer_name:
            layer_name = layer_name.replace('customtagneg', '')
            if layer_name in self.ATTRIBUTE_TRANSLATION_DICT:
                layer_name = self.ATTRIBUTE_TRANSLATION_DICT[layer_name][0]
        if layer_name in self.ATTRIBUTE_TRANSLATION_DICT:
            layer_name = self.ATTRIBUTE_TRANSLATION_DICT[layer_name]
        else:
            # Remove the attached package to get the raw name.
            layer_name = layer_name.split('-')[0].capitalize()
        # Append unit if exist
        if org_layer_name in self.ATTRIBUTE_UNIT_DICT and self.ATTRIBUTE_UNIT_DICT[org_layer_name] is not None:
            layer_unit = self.update_unit_string(self.ATTRIBUTE_UNIT_DICT[org_layer_name], length_unit, time_unit)
        return layer_name, layer_unit

    @staticmethod
    def update_unit_string(unit_string, length_unit, time_unit):
        if '#lenunit#' in unit_string:
            unit_string = unit_string.replace('#lenunit#', length_unit.capitalize())
        if '#timeunit#' in unit_string:
            unit_string = unit_string.replace('#timeunit#', time_unit.capitalize())
        return unit_string

    @staticmethod
    def transform(x, y, inprj, outprj):
        if "+" in inprj:
            inprj = pyproj.Proj(str(inprj), preserve_units=True)
        else:
            inprj = pyproj.Proj(init='epsg:' + str(inprj), preserve_units=True)

        if "+" in outprj:
            outprj = pyproj.Proj(str(outprj), preserve_units=True)
        else:
            outprj = pyproj.Proj(init='epsg:' + str(outprj), preserve_units=True)
        x, y = pyproj.transform(inprj, outprj, x, y)
        return x, y

    def create_extent_for_project(self, xll, yll, rotation, model_epsg):
        """
        Returns:
            4-list: Extent bounding box (e.g.: [minx, miny, maxx, maxy] ).
        """
        # Check if property is already set to save time
        if not self.map_extents:
            # Load flopy model if not already done
            if not self.flopy_model:
                self.load_model()

            geo_prj = '4326'

            prj = flopy.utils.reference.getproj4(model_epsg)

            # Spatial Reference
            sr = flopy.utils.reference.SpatialReference(delr=self.flopy_model.dis.delr, delc=self.flopy_model.dis.delc,
                                                        xll=float(xll), yll=float(yll), rotation=float(rotation),
                                                        proj4_str=prj)
            self.flopy_model.sr = sr

            model_xmin, model_xmax, model_ymin, model_ymax = self.flopy_model.sr.get_extent()

            geo_xmin, geo_ymin = self.transform(model_xmin, model_ymin, str(model_epsg), geo_prj)
            geo_xmax, geo_ymax = self.transform(model_xmax, model_ymax, str(model_epsg), geo_prj)
            self.map_extents = [geo_xmin, geo_ymin, geo_xmax, geo_ymax]

        return self.map_extents

    def get_extent_for_project(self, model_db):
        """
        Returns:
            4-list: Extent bounding box (e.g.: [minx, miny, maxx, maxy] ).
        """
        # Check if property is already set to save time
        if not self.map_extents:
            db_id = model_db.get_id()
            Session = model_db._app.get_persistent_store_database('primary_db', as_sessionmaker=True)
            session = Session()

            # Get resource_id and name by querying the resource with database_id
            resources = session.query(ModflowModelResource).all()
            model_extents = [-180, -90, 180, 90]
            for resource in resources:
                attributes = json.loads(resource._attributes)
                if attributes['database_id'] == db_id:
                    if 'model_extents' in attributes:
                        model_extents = json.loads(attributes['model_extents'])
                    break
            self.map_extents = model_extents

        return self.map_extents

    def get_projection_string(self):
        """
        Returns:
            The spatial reference projection string for the modflow model.
        """
        if not self.flopy_model:
            self.load_model()

        return self.flopy_model.sr.proj4_str

    def get_projection_units(self):
        """
        Returns:
            The spatial reference projection units.
        """
        if not self.flopy_model:
            self.load_model()

        return self.flopy_model.sr.units

    def modify_spatial_reference(self,
                                 delr=None,
                                 delc=None,
                                 xll=None,
                                 yll=None,
                                 rotation=None,
                                 epsg=None,
                                 proj4_str=None,
                                 units=None,
                                 lenuni=None):
        """
        Modify existing spatial reference for modlow model instance

        Args:
            delr(array): the model discretization delr vector (An array of spacings along a row)
            delc(array): the model discretization delc vector (An array of spacings along a column)
            xll(float): the x coordinate of the lower left corner of the grid
            yll(float): the y coordinate of the lower left corner of the grid
            rotation(float): the counter-clockwise rotation (in degrees) of the grid
            epsg(str): EPSG code that identifies the grid in space.
            proj4_str(str): Proj4_str
            units(str): meters or feet
            lenuni(int): model units 1-'feet' and 2-'meters'
        Returns:
            The modflow spatial reference object.
        """
        if not self.flopy_model:
            self.load_model()

        if not delr:
            delr = self.flopy_model.dis.delr

        if not delc:
            delc = self.flopy_model.dis.delc

        if not xll:
            xll = self.flopy_model.sr.xll

        if not yll:
            yll = self.flopy_model.sr.yll

        if not units:
            units = self.flopy_model.sr.units

        if not rotation:
            rotation = self.flopy_model.sr.rotation

        if not epsg:
            epsg = self.flopy_model.sr.epsg

        if not proj4_str:
            proj4_str = self.flopy_model.sr.proj4_str

        if not lenuni:
            lenuni = self.flopy_model.sr.lenuni

        self.flopy_model.sr = SpatialReference(delr=delr,
                                               delc=delc,
                                               xll=xll,
                                               yll=yll,
                                               rotation=rotation,
                                               epsg=epsg,
                                               proj4_str=proj4_str,
                                               units=units,
                                               lenuni=lenuni
                                               )
        return self.flopy_model.sr

    def get_head_data(self):
        """
        Gets the head data from the hds file if it exists
        Returns:
            bf.HeadFile(hds).get_data()
        """
        # Load flopy model if not already loaded
        if not self.flopy_model:
            self.load_model()

        model_file_list = self.model_file_db.list()
        hds_file = None

        # loop through model file database for a .hds file
        for file in model_file_list:
            if file.split(".")[-1] in ['hds', 'hed']:
                hds_file = os.path.join(self.model_file_db.db_dir, file)

        # If .hds file exists, get heads data
        if hds_file:
            hdsobj = bf.HeadFile(hds_file)
            hds = hdsobj.get_data()
            return hds
        else:
            return None

    def get_package_layer_attribute_info(self):
        """
        gets the attribute names for the package layers as well as the minimum and maximum values for the attributes
        Returns:
            layer_dict(dict): {"package":{"layer":{maximum:..., minimum:...}}}
        """
        # Load flopy model if not already loaded
        if not self.flopy_model:
            self.load_model()

        layer_dict = {}

        # Loop through all the flopy packages in the model
        for package_extension in self.flopy_model.get_package_list():
            layer_dict[package_extension] = {}
            pak = self.flopy_model.get_package(package_extension)
            attrs = dir(pak)
            if 'sr' in attrs:
                attrs.remove('sr')
            if 'start_datetime' in attrs:
                attrs.remove('start_datetime')
            # Create arrays for the attributes in packages and save the min and max to a dict
            for attr in attrs:
                a = pak.__getattribute__(attr)
                if isinstance(a, Util2d) and a.shape == (self.flopy_model.nrow, self.flopy_model.ncol):
                    name = a.name.lower()
                    arr = a.array
                    arr = self.compress_array(arr, self.flopy_model.bas6.ibound[0].array)
                    minval, maxval = self.get_min_max_non_zeros(arr)
                    layer_dict[package_extension][name] = {'minimum': minval, 'maximum': maxval}
                elif isinstance(a, Util3d):
                    for i, u2d in enumerate(a):
                        name = shape_attr_name(u2d.name)
                        name += '_{:03d}'.format(i + 1)
                        arr = u2d.array
                        arr = self.compress_array(arr, self.flopy_model.bas6.ibound[i].array)
                        minval, maxval = self.get_min_max_non_zeros(arr)
                        layer_dict[package_extension][name] = {'minimum': minval, 'maximum': maxval}
                elif isinstance(a, Transient2d):
                    kpers = list(a.transient_2ds.keys())
                    kpers.sort()
                    for kper in kpers:
                        if kper in self.STRESS_PERIOD_IMPORT:
                            u2d = a.transient_2ds[kper]
                            name = shape_attr_name(u2d.name)
                            name = "{}_{:03d}".format(name, kper + 1)
                            arr = u2d.array
                            arr = self.compress_array(arr, self.flopy_model.bas6.ibound[0].array)
                            minval, maxval = self.get_min_max_non_zeros(arr)
                            layer_dict[package_extension][name] = {'minimum': minval, 'maximum': maxval}
                elif isinstance(a, MfList):
                    kpers = a.data.keys()
                    for kper in kpers:
                        if kper in self.STRESS_PERIOD_IMPORT:
                            arrays = a.to_array(kper)
                            for name, array in arrays.items():
                                flopy_package_name = "{}-{}".format(name, package_extension.lower())
                                if flopy_package_name in self.ATTRIBUTE_TRANSLATION_DICT \
                                        and isinstance(self.ATTRIBUTE_TRANSLATION_DICT[flopy_package_name], list):
                                    positive_array = np.copy(array)
                                    negative_array = np.copy(array)

                                    # Positive Array
                                    positive_array[positive_array < 0] = 0
                                    # Negative Array
                                    negative_array[negative_array > 0] = 0
                                    negative_array = np.absolute(negative_array)

                                    list_loop = {'customtagpos': positive_array, 'customtagneg': negative_array}
                                    for key, new_array in list_loop.items():
                                        name = shape_attr_name(name, length=4) + key
                                        for k in range(new_array.shape[0]):
                                            aname = "{}{:03d}{:03d}".format(name, k + 1, kper + 1)
                                            arr = new_array[k].astype(np.float32)
                                            arr = self.compress_array(arr, self.flopy_model.bas6.ibound[k].array)
                                            minval, maxval = self.get_min_max_non_zeros(arr)
                                            layer_dict[package_extension][aname] = {'minimum': minval,
                                                                                    'maximum': maxval}
                                else:
                                    for k in range(array.shape[0]):
                                        name = shape_attr_name(name, length=4)
                                        aname = "{}{:03d}{:03d}".format(name, k + 1,
                                                                        kper + 1)
                                        arr = array[k].astype(np.float32)
                                        arr = self.compress_array(arr, self.flopy_model.bas6.ibound[k].array)
                                        minval, maxval = self.get_min_max_non_zeros(arr)
                                        layer_dict[package_extension][aname] = {'minimum': minval, 'maximum': maxval}
                elif isinstance(a, list):
                    for v in a:
                        if isinstance(v, Util3d):
                            for i, u2d in enumerate(v):
                                name = shape_attr_name(u2d.name)
                                name += '_{:03d}'.format(i + 1)
                                arr = u2d.array
                                arr = self.compress_array(arr, self.flopy_model.bas6.ibound[i].array)
                                minval, maxval = self.get_min_max_non_zeros(arr)
                                layer_dict[package_extension][name] = {'minimum': minval, 'maximum': maxval}

        return layer_dict

    def get_head_info(self):
        """
        gets the max and min values for the head layers
        Returns:
            layer_dict(dict): {"layer":{maximum:..., minimum:...}}
        """
        # Load flopy model if not already loaded
        if not self.flopy_model:
            self.load_model()

        hds = self.get_head_data()
        if hds is not None:
            head_info = {}
            if hds is None:
                return None
            else:
                # Get min and max values for each layer of heads in the model
                for i, hdslayer in enumerate(hds):
                    hdslayer[hdslayer == self.flopy_model.bas6.hnoflo] = np.nan
                    head_info[str(i + 1)] = {'minimum': np.nanmin(hdslayer), 'maximum': np.nanmax(hdslayer)}

                return head_info

    def upload_tif(self, package, attribute, arr, multiple_values=True):
        """
        Create a GEOTIFF for the package attribute and uploads the tif to geoserver
        Args:
            package (str): modflow package name (i.e DIS, BAS6, etc)
            attribute (str): attribute name within the package (i.e model_top for the DIS package)
            arr (str): numpy array for the given package attribute
            multiple_values (bool): True if have more than one value, False if only has one value.
        """

        if multiple_values:
            if package in self.LOW_BLUE_STYLE_PACKAGE:
                style_name_ext = self.RL_LOWBLUE
            else:
                style_name_ext = self.RL
        else:
            style_name_ext = self.RL1

        # Get unique name for the package attribute
        geoserver_file_name = self.get_unique_item_name("{}-{}".format(package, attribute),
                                                        model_file_db=self.model_file_db)
        tmp_raster = "{}.tif".format(geoserver_file_name)
        tmp_raster2 = "{}_temp.tif".format(geoserver_file_name)
        tmp_prj = '{}.prj'.format(geoserver_file_name)
        tmp_zip = '{}.zip'.format(geoserver_file_name)

        # Create GEOTIFF and .prj file from flopy
        self.flopy_model.sr.export_array(tmp_raster2, arr)

        # Crop the raster using boundary layer
        # self.crop_reproject_raster(dst_src, tmp_raster2, tmp_raster)
        self.crop_raster(tmp_raster2, tmp_raster)
        proj = flopy.utils.reference.getprj(self.flopy_model.sr.epsg)
        with open(tmp_prj, 'w') as f:
            f.write(proj)

        # Zip the GEOTIFF and .prj file together
        zipf = zipfile.ZipFile(tmp_zip, 'w', zipfile.ZIP_DEFLATED)
        zipf.write(tmp_raster)
        zipf.write(tmp_prj)
        zipf.close()

        # Upload the zipped folder to geoserver
        geoserver_store = "{}:{}".format(self.WORKSPACE, geoserver_file_name)
        self.gs_engine.create_coverage_resource(geoserver_store,
                                                overwrite=True,
                                                coverage_file=tmp_zip,
                                                coverage_type='geotiff')

        # Update the geoserer resource with the correct style, crs, enable, and projection_policy
        style_name = "{}_{}".format(self.WORKSPACE, style_name_ext)
        self.gs_engine.update_layer(layer_id=geoserver_store,
                                    default_style=style_name)
        self.gs_engine.update_resource(resource_id=geoserver_store,
                                       projection="EPSG:{}".format(self.flopy_model.sr.epsg),
                                       enabled=True)

        # Delete temporary files
        os.remove(tmp_raster)
        os.remove(tmp_raster2)
        os.remove(tmp_prj)
        os.remove(tmp_zip)

    @reload_config()
    def create_model_boundary_style(self, overwrite=True, reload_config=True):
        """
        Create style for models boundary layers.
        Args:
            overwrite(bool): Overwrite style if already exists when True. Defaults to False.
            reload_config(bool): Reload the GeoServer node configuration and catalog before returning if True.
        """
        # Create Base Style
        context = {}
        self.gs_api.create_style(
            workspace=self.WORKSPACE,
            style_name=self.VL_MODEL_BOUNDARY,
            sld_template=os.path.join(self.SLD_PATH, self.VL_MODEL_BOUNDARY + '.sld'),
            sld_context=context,
            overwrite=overwrite
        )

    @reload_config()
    def create_model_grid_style(self, overwrite=True, reload_config=True):
        """
        Create style for models boundary layers.
        Args:
            overwrite(bool): Overwrite style if already exists when True. Defaults to False.
            reload_config(bool): Reload the GeoServer node configuration and catalog before returning if True.
        """
        # Create Base Style
        context = {}
        self.gs_api.create_style(
            workspace=self.WORKSPACE,
            style_name=self.VL_MODEL_GRID,
            sld_template=os.path.join(self.SLD_PATH, self.VL_MODEL_GRID + '.sld'),
            sld_context=context,
            overwrite=overwrite
        )

    @reload_config()
    def delete_model_grid_style(self, purge=True, reload_config=True):
        """
        Delete model boundary style.
        Args:
            purge(bool): Force remove all resources associated with style.
            reload_config(bool): Reload the GeoServer node configuration and catalog before returning if True.
        """
        # Delete Base Style
        self.gs_api.delete_style(
            workspace=self.WORKSPACE,
            style_name=self.VL_MODEL_GRID,
            purge=purge
        )

    @reload_config()
    def delete_model_boundary_style(self, purge=True, reload_config=True):
        """
        Delete model boundary style.
        Args:
            purge(bool): Force remove all resources associated with style.
            reload_config(bool): Reload the GeoServer node configuration and catalog before returning if True.
        """
        # Delete Base Style
        self.gs_api.delete_style(
            workspace=self.WORKSPACE,
            style_name=self.VL_MODEL_BOUNDARY,
            purge=purge
        )

    @reload_config()
    def create_model_boundary_layer(self, reload_config=True):
        """
        Create and Upload a model boundary shapefile to geoserver. Creates store (if it doesn't
        exist), feature type resource, and a layer.
        """
        # Load flopy model if not already loaded
        if not self.flopy_model:
            self.load_model()

        tmp_grid_name = 'temp_grid'
        tmp_grid_shapefile = "{}.shp".format(tmp_grid_name)

        # Open the gridded shapefile, select the values with Ibound not 0, and make a union from them
        gdf_boundary = []
        for layer in range(self.flopy_model.dis.nlay):
            print("number of layer is:" + str(self.flopy_model.dis.nlay))
            self.flopy_model.bas6.ibound[layer].export(tmp_grid_shapefile)
            gdf = geopandas.read_file(tmp_grid_shapefile)
            ibound_col = 'ibound__' + str(layer)
            if layer > 0:
                gdf_boundary.append(gdf[gdf[ibound_col] != 0], sort=False)
            else:
                gdf_boundary = gdf[gdf[ibound_col] != 0]
        self._boundary = gdf_boundary.geometry.unary_union

        # Get names of geoserver files
        geoserver_boundary_file_name = self.get_unique_item_name(self.VL_MODEL_BOUNDARY,
                                                                 model_file_db=self.model_file_db)
        tmp_boundary_shapefile = "{}.shp".format(geoserver_boundary_file_name)
        tmp_dbf = "{}.dbf".format(geoserver_boundary_file_name)
        tmp_shx = "{}.shx".format(geoserver_boundary_file_name)
        tmp_prj = '{}.prj'.format(geoserver_boundary_file_name)
        tmp_zip = '{}.zip'.format(geoserver_boundary_file_name)

        # Create a single polygon shapefile from the unioned gridded shapefile
        schema = {
            'geometry': 'Polygon',
            'properties': {'id': 'str'},
        }

        with fiona.open(tmp_boundary_shapefile, 'w', 'ESRI Shapefile', schema) as c:
            c.write({
                'geometry': mapping(self._boundary),
                'properties': {'id': 'boundary'},
            })

        # Create a .prj file
        proj = flopy.utils.reference.getprj(self.flopy_model.sr.epsg)
        with open(tmp_prj, 'w') as f:
            f.write(proj)

        # Zip the .prj file with the single polygon shapefile and necessary extensions
        zipf = zipfile.ZipFile(tmp_zip, 'w', zipfile.ZIP_DEFLATED)
        zipf.write(tmp_boundary_shapefile)
        zipf.write(tmp_dbf)
        zipf.write(tmp_shx)
        zipf.write(tmp_prj)
        zipf.close()

        # Create geoserver resource with the zip file
        geoserver_engine = self.gs_engine
        geoserver_store = "{}:{}".format(self.WORKSPACE, geoserver_boundary_file_name)
        geoserver_engine.create_shapefile_resource(geoserver_store,
                                                   overwrite=True,
                                                   shapefile_zip=tmp_zip)

        # Update geoserver resource with correct parameters
        style_name = self.VL_MODEL_BOUNDARY
        self.gs_engine.update_layer(layer_id=geoserver_store,
                                    default_style=style_name)
        self.gs_engine.update_resource(resource_id=geoserver_store,
                                       projection="EPSG:{}".format(self.flopy_model.sr.epsg),
                                       projection_policy="FORCE_DECLARED",
                                       enabled=True)

        # Get model boundary layer group from geoserver
        boundary_group_name = "{}:{}".format(self.WORKSPACE, self.VL_MODEL_BOUNDARY)
        style_name = self.VL_MODEL_BOUNDARY
        response = self.gs_engine.get_layer_group(boundary_group_name)

        # If layer group exists, get existing layers/styles and update with new layer/style
        if response['success']:
            layers = response['result']['layers']
            styles = response['result']['styles']
            layers.append(geoserver_boundary_file_name)
            styles.append(style_name)
            self.gs_engine.update_layer_group(layer_group_id=boundary_group_name,
                                              layers=layers,
                                              styles=styles
                                              )
        # Create new layer group if model boundary layer group doesn't exist
        else:
            if not self.model_selection_bounds:
                self.model_selection_bounds = ['-180', '180', '-90', '90']
            self.model_selection_bounds.append('4326')
            self.gs_engine.create_layer_group(layer_group_id=boundary_group_name,
                                              layers=(geoserver_boundary_file_name,),
                                              styles=(style_name,),
                                              bounds=self.model_selection_bounds
                                              )

        # Clean up shapefiles that aren't needed anymore
        os.remove(tmp_grid_shapefile)
        os.remove("{}.shx".format(tmp_grid_name))
        os.remove("{}.dbf".format(tmp_grid_name))

        os.remove(tmp_boundary_shapefile)
        os.remove("{}.shx".format(geoserver_boundary_file_name))
        os.remove("{}.dbf".format(geoserver_boundary_file_name))
        os.remove("{}.prj".format(geoserver_boundary_file_name))
        os.remove("{}.cpg".format(geoserver_boundary_file_name))
        os.remove("{}.zip".format(geoserver_boundary_file_name))

        # Create Model Grid
        # Get bottom elevation and append to gdf_boundary (model grid)
        botm_array = self.flopy_model.dis.botm[self.flopy_model.dis.nlay - 1].array
        top_array = self.flopy_model.dis.top.array
        thickness_array = top_array - botm_array
        i = 0
        thickness_one_dimension_array = []

        # Create IJ dataframe with bottom elevation assigned to it.
        botm_IJ = []
        for row in range(self.flopy_model.dis.nrow):
            for col in range(self.flopy_model.dis.ncol):
                if i in gdf_boundary.index:
                    thickness_one_dimension_array.append(thickness_array[row][col])
                    botm_IJ.append(i)
                i += 1
        thickness_df = pandas.DataFrame({'IJ': botm_IJ, 'thickness': thickness_one_dimension_array})

        # Duplicate orginal geopandas dataframe index to IJ
        gdf_boundary['IJ'] = gdf_boundary.index

        # Merge bottom dataframe dataset using IJ data
        gdf_boundary = gdf_boundary.merge(thickness_df, on='IJ')

        geoserver_grid_file_name = self.get_unique_item_name(self.VL_MODEL_GRID, model_file_db=self.model_file_db)

        # Create shapefile
        tmp_grid_shapefile = "{}.shp".format(geoserver_grid_file_name)
        tmp_grid_dbf = "{}.dbf".format(geoserver_grid_file_name)
        tmp_grid_shx = "{}.shx".format(geoserver_grid_file_name)
        tmp_grid_cpg = '{}.cpg'.format(geoserver_grid_file_name)
        tmp_grid_zip = '{}.zip'.format(geoserver_grid_file_name)
        gdf_boundary.to_file(tmp_grid_shapefile)

        # Zip the shapefile
        zipf = zipfile.ZipFile(tmp_grid_zip, 'w', zipfile.ZIP_DEFLATED)
        zipf.write(tmp_grid_shapefile)
        zipf.write(tmp_grid_dbf)
        zipf.write(tmp_grid_shx)
        zipf.write(tmp_grid_cpg)
        zipf.close()

        # Create geoserver resource with the zip file
        geoserver_engine = self.gs_engine
        geoserver_store = "{}:{}".format(self.WORKSPACE, geoserver_grid_file_name)
        geoserver_engine.create_shapefile_resource(geoserver_store,
                                                   overwrite=True,
                                                   shapefile_zip=tmp_grid_zip)

        # Update geoserver resource with correct parameters
        style_name = self.VL_MODEL_GRID
        self.gs_engine.update_layer(layer_id=geoserver_store,
                                    default_style=style_name)
        self.gs_engine.update_resource(resource_id=geoserver_store,
                                       projection="EPSG:{}".format(self.flopy_model.sr.epsg),
                                       projection_policy="FORCE_DECLARED",
                                       enabled=True)

        # Get model boundary layer group from geoserver
        style_name = self.VL_MODEL_GRID
        response = self.gs_engine.get_layer_group(boundary_group_name)

        # If layer group exists, get existing layers/styles and update with new layer/style
        if response['success']:
            layers = response['result']['layers']
            styles = response['result']['styles']
            layers.append(geoserver_grid_file_name)
            styles.append(style_name)
            self.gs_engine.update_layer_group(layer_group_id=boundary_group_name,
                                              layers=layers,
                                              styles=styles
                                              )

        # Clean up shapefiles that aren't needed anymore
        # os.remove(tmp_grid_shapefile)
        # os.remove(tmp_grid_dbf)
        # os.remove(tmp_grid_shx)
        # os.remove(tmp_grid_cpg)
        # os.remove("{}.zip".format(geoserver_grid_file_name))

    @reload_config()
    def delete_model_boundary_layer(self, reload_config=True):
        """
        Deletes geoserver resources for the model boundary
        """
        # Load flopy model if not already loaded
        if not self.flopy_model:
            self.load_model()

        # Delete model boundary layer
        geoserver_engine = self.gs_engine
        geoserver_file_name = self.get_unique_item_name(self.VL_MODEL_BOUNDARY, model_file_db=self.model_file_db)
        geoserver_store = "{}:{}".format(self.WORKSPACE, geoserver_file_name)
        geoserver_engine.delete_resource(geoserver_store)

    @reload_config()
    def create_package_shapefile_layers(self, reload_config=True):
        """
        Create and Upload a shapefile to geoserver for all packages in the modflow model. Creates store (if it doesn't
        exist), feature type resource, and a layer.
        """
        # Load flopy model if not already loaded
        if not self.flopy_model:
            self.load_model()

        # Loop through all the flopy packages in the model
        for package_extension in self.flopy_model.get_package_list():
            pak = self.flopy_model.get_package(package_extension)
            attrs = dir(pak)
            if 'sr' in attrs:
                attrs.remove('sr')
            if 'start_datetime' in attrs:
                attrs.remove('start_datetime')
            # Create arrays for the attributes in packages and upload them to geoserver with upload_tif method
            for attr in attrs:
                a = pak.__getattribute__(attr)
                if isinstance(a, Util2d) and a.shape == (self.flopy_model.nrow, self.flopy_model.ncol):
                    name = a.name.lower()
                    arr = a.array
                    compress_arr = self.compress_array(arr, self.flopy_model.bas6.ibound[0].array)
                    multiple_values = True
                    minval, maxval = self.get_min_max_non_zeros(compress_arr)
                    if minval == maxval:
                        multiple_values = False
                    self.upload_tif(package_extension, name, arr, multiple_values)
                elif isinstance(a, Util3d):
                    for i, u2d in enumerate(a):
                        name = shape_attr_name(u2d.name)
                        name += '_{:03d}'.format(i + 1)
                        arr = u2d.array
                        compress_arr = self.compress_array(arr, self.flopy_model.bas6.ibound[i].array)
                        multiple_values = True
                        minval, maxval = self.get_min_max_non_zeros(compress_arr)
                        if minval == maxval:
                            multiple_values = False
                        self.upload_tif(package_extension, name, arr, multiple_values)
                elif isinstance(a, Transient2d):
                    kpers = list(a.transient_2ds.keys())
                    kpers.sort()
                    for kper in kpers:
                        if kper in self.STRESS_PERIOD_IMPORT:
                            u2d = a.transient_2ds[kper]
                            name = shape_attr_name(u2d.name)
                            name = "{}_{:03d}".format(name, kper + 1)
                            arr = u2d.array
                            compress_arr = self.compress_array(arr, self.flopy_model.bas6.ibound[0].array)
                            multiple_values = True
                            minval, maxval = self.get_min_max_non_zeros(compress_arr)
                            if minval == maxval:
                                multiple_values = False
                            self.upload_tif(package_extension, name, arr, multiple_values)
                elif isinstance(a, MfList):
                    kpers = a.data.keys()
                    for kper in kpers:
                        if kper in self.STRESS_PERIOD_IMPORT:
                            arrays = a.to_array(kper)
                            for name, array in arrays.items():
                                flopy_package_name = "{}-{}".format(name, package_extension.lower())
                                for k in range(array.shape[0]):
                                    if flopy_package_name in self.ATTRIBUTE_TRANSLATION_DICT \
                                            and isinstance(self.ATTRIBUTE_TRANSLATION_DICT[flopy_package_name], list):
                                        # Positive Array
                                        positive_array = np.copy(array)
                                        positive_array[positive_array < 0] = 0

                                        # Negative Array
                                        negative_array = np.copy(array)
                                        negative_array[negative_array > 0] = 0
                                        negative_array = np.absolute(negative_array)

                                        list_loop = {'customtagpos': positive_array, 'customtagneg': negative_array}
                                        for key, new_array in list_loop.items():
                                            name = shape_attr_name(name, length=4) + key
                                            aname = "{}{:03d}{:03d}".format(name, k + 1,
                                                                            kper + 1)
                                            arr = new_array[k].astype(np.float32)
                                            compress_arr = self.compress_array(arr,
                                                                               self.flopy_model.bas6.ibound[k].array)
                                            minval, maxval = self.get_min_max_non_zeros(compress_arr)
                                            if minval == maxval:
                                                multiple_values = False
                                            self.upload_tif(package_extension, aname, arr, multiple_values)
                                    else:
                                        name = shape_attr_name(name, length=4)
                                        aname = "{}{:03d}{:03d}".format(name, k + 1,
                                                                        kper + 1)
                                        arr = array[k].astype(np.float32)
                                        compress_arr = self.compress_array(arr, self.flopy_model.bas6.ibound[k].array)
                                        multiple_values = True
                                        minval, maxval = self.get_min_max_non_zeros(compress_arr)
                                        if minval == maxval:
                                            multiple_values = False
                                        self.upload_tif(package_extension, aname, arr, multiple_values)
                elif isinstance(a, list):
                    for v in a:
                        if isinstance(v, Util3d):
                            for i, u2d in enumerate(v):
                                name = shape_attr_name(u2d.name)
                                name += '_{:03d}'.format(i + 1)
                                arr = u2d.array
                                compress_arr = self.compress_array(arr, self.flopy_model.bas6.ibound[i].array)
                                multiple_values = True
                                minval, maxval = self.get_min_max_non_zeros(compress_arr)
                                if minval == maxval:
                                    multiple_values = False
                                self.upload_tif(package_extension, name, arr, multiple_values)

    @reload_config()
    def delete_package_shapefile_layers(self, reload_config=True):
        """
        Deletes geoserver resources for all packages in the modflow model
        """
        # Loop through all the flopy packages in the model
        if not self.flopy_model:
            self.load_model()

        geoserver_engine = self.gs_engine

        # Loop through all the pac
        for package_extension in self.flopy_model.get_package_list():
            pak = self.flopy_model.get_package(package_extension)
            attrs = dir(pak)
            if 'sr' in attrs:
                attrs.remove('sr')
            if 'start_datetime' in attrs:
                attrs.remove('start_datetime')
            # Get names of each package attribute and delete from geoserver
            for attr in attrs:
                a = pak.__getattribute__(attr)
                if isinstance(a, Util2d) and a.shape == (self.flopy_model.nrow, self.flopy_model.ncol):
                    name = a.name.lower()
                    geoserver_file_name = self.get_unique_item_name("{}-{}".format(package_extension, name),
                                                                    model_file_db=self.model_file_db)
                    geoserver_store = "{}:{}".format(self.WORKSPACE, geoserver_file_name)
                    geoserver_engine.delete_resource(geoserver_store)
                elif isinstance(a, Util3d):
                    for i, u2d in enumerate(a):
                        name = shape_attr_name(u2d.name)
                        name += '_{:03d}'.format(i + 1)
                        geoserver_file_name = self.get_unique_item_name("{}-{}".format(package_extension, name),
                                                                        model_file_db=self.model_file_db)
                        geoserver_store = "{}:{}".format(self.WORKSPACE, geoserver_file_name)
                        geoserver_engine.delete_resource(geoserver_store)
                elif isinstance(a, Transient2d):
                    kpers = list(a.transient_2ds.keys())
                    kpers.sort()
                    for kper in kpers:
                        u2d = a.transient_2ds[kper]
                        name = shape_attr_name(u2d.name)
                        name = "{}_{:03d}".format(name, kper + 1)
                        geoserver_file_name = self.get_unique_item_name("{}-{}".format(package_extension, name),
                                                                        model_file_db=self.model_file_db)
                        geoserver_store = "{}:{}".format(self.WORKSPACE, geoserver_file_name)
                        geoserver_engine.delete_resource(geoserver_store)
                elif isinstance(a, MfList):
                    kpers = a.data.keys()
                    for kper in kpers:
                        arrays = a.to_array(kper)
                        for name, array in arrays.items():
                            for k in range(array.shape[0]):
                                name = shape_attr_name(name, length=4)
                                aname = "{}{:03d}{:03d}".format(name, k + 1,
                                                                kper + 1)
                                geoserver_file_name = self.get_unique_item_name("{}-{}".format(
                                                                                    package_extension,
                                                                                    aname
                                                                                ),
                                                                                model_file_db=self.model_file_db)
                                geoserver_store = "{}:{}".format(self.WORKSPACE, geoserver_file_name)
                                geoserver_engine.delete_resource(geoserver_store)
                elif isinstance(a, list):
                    for v in a:
                        if isinstance(v, Util3d):
                            for i, u2d in enumerate(v):
                                name = shape_attr_name(u2d.name)
                                name += '_{:03d}'.format(i + 1)
                                geoserver_file_name = self.get_unique_item_name("{}-{}".format(package_extension, name),
                                                                                model_file_db=self.model_file_db)
                                geoserver_store = "{}:{}".format(self.WORKSPACE, geoserver_file_name)
                                geoserver_engine.delete_resource(geoserver_store)

    @reload_config()
    def create_raster_style(self, overwrite=True, reload_config=True):
        """
        Create styles for head raster layers.
        Args:
            overwrite(bool): Overwrite style if already exists when True. Defaults to False.
            reload_config(bool): Reload the GeoServer node configuration and catalog before returning if True.
        """
        # Create Base Style
        context = {}
        self.gs_api.create_style(
            workspace=self.WORKSPACE,
            style_name="{}_{}".format(self.WORKSPACE, self.RL),
            sld_template=os.path.join(self.SLD_PATH, self.RL + '.sld'),
            sld_context=context,
            overwrite=overwrite
        )

        self.gs_api.create_style(
            workspace=self.WORKSPACE,
            style_name="{}_{}".format(self.WORKSPACE, self.RL1),
            sld_template=os.path.join(self.SLD_PATH, self.RL1 + '.sld'),
            sld_context=context,
            overwrite=overwrite
        )

        self.gs_api.create_style(
            workspace=self.WORKSPACE,
            style_name="{}_{}".format(self.WORKSPACE, self.RL_LOWBLUE),
            sld_template=os.path.join(self.SLD_PATH, self.RLLB + '.sld'),
            sld_context=context,
            overwrite=overwrite
        )

    @reload_config()
    def delete_raster_style(self, purge=True, reload_config=True):
        """
        Delete styles for head raster layers.
        Args:
            purge(bool): Force remove all resources associated with style.
            reload_config(bool): Reload the GeoServer node configuration and catalog before returning if True.
        """
        # Delete Base Style
        self.gs_api.delete_style(
            workspace=self.WORKSPACE,
            style_name="{}_{}".format(self.WORKSPACE, self.RL),
            purge=purge
        )

        self.gs_api.delete_style(
            workspace=self.WORKSPACE,
            style_name="{}_{}".format(self.WORKSPACE, self.RL1),
            purge=purge
        )

    @reload_config()
    def create_head_raster_layer(self, reload_config=True):
        """
        Creates the head raster layer. Creates store (if it doesn't exist), feature type resource, and a layer.

        Args:
            reload_config(bool): Reload the GeoServer node configuration and catalog before returning if True
        """
        # Get head data
        hds = self.get_head_data()

        if hds is not None:
            geoserver_engine = self.gs_engine
            # Loop through the head layers
            for i, hdslayer in enumerate(hds):
                # Get names for the head raster for the specific layer
                raster_name = self.get_unique_item_name(self.RL_HEAD, model_file_db=self.model_file_db)
                geoserver_raster_file_name = '{}_{}'.format(raster_name, str(i + 1).zfill(3))
                tmp_raster = '{}.tif'.format(geoserver_raster_file_name)
                tmp_prj = '{}.prj'.format(geoserver_raster_file_name)
                tmp_zip = '{}.zip'.format(geoserver_raster_file_name)
                nodatavalue = float(self.flopy_model.bas6.hnoflo)
                # Create GEOTIFF for the specific layer for the head raster
                self.flopy_model.sr.export_array(tmp_raster, hdslayer, nodata=nodatavalue)

                # Create .prj file and zip with GEOTIFF
                proj = flopy.utils.reference.getprj(self.flopy_model.sr.epsg)
                with open(tmp_prj, 'w') as f:
                    f.write(proj)
                zipf = zipfile.ZipFile(tmp_zip, 'w', zipfile.ZIP_DEFLATED)
                zipf.write(tmp_raster)
                zipf.write(tmp_prj)
                zipf.close()

                # Upload GEOTIFF to the geoserver
                geoserver_store = "{}:{}".format(self.WORKSPACE, geoserver_raster_file_name)
                geoserver_engine.create_coverage_resource(geoserver_store,
                                                          overwrite=True,
                                                          coverage_file=tmp_zip,
                                                          coverage_type='geotiff')

                # Update the resource with correct parameters
                style_name = "{}_{}".format(self.WORKSPACE, self.RL)
                self.gs_engine.update_layer(layer_id=geoserver_store,
                                            default_style=style_name)
                self.gs_engine.update_resource(resource_id=geoserver_store,
                                               projection="EPSG:{}".format(self.flopy_model.sr.epsg),
                                               projection_policy="FORCE_DECLARED",
                                               enabled=True,)

                # Clean up unnecessary files
                os.remove(tmp_raster)
                os.remove(tmp_zip)
                os.remove(tmp_prj)

    @reload_config()
    def delete_head_raster_layer(self, reload_config=True):
        """
        Deletes the head raster resource.
        """
        hds = self.get_head_data()

        if hds is not None:
            geoserver_engine = self.gs_engine
            for i, hdslayer in enumerate(hds):
                raster_name = self.get_unique_item_name(self.RL_HEAD, model_file_db=self.model_file_db)
                geoserver_raster_file_name = '{}_{}'.format(raster_name, str(i + 1).zfill(3))
                geoserver_store = "{}:{}".format(self.WORKSPACE, geoserver_raster_file_name)
                geoserver_engine.delete_resource(geoserver_store)

    # TODO: Fix this with writing prj file and zipping
    @reload_config()
    def create_head_contour_layer(self, reload_config=True):
        """
        Creates the head contour layer. Creates store (if it doesn't exist), feature type resource, and a layer.

        Args:
            reload_config(bool): Reload the GeoServer node configuration and catalog before returning if True
        """
        hds = self.get_head_data()

        if hds is not None:
            geoserver_engine = self.gs_engine
            for i, hdslayer in enumerate(hds):
                contour_name = self.get_unique_item_name(self.VL_HEAD_CONTOUR, model_file_db=self.model_file_db)
                geoserver_contour_file_name = '{}_{}'.format(contour_name, str(i + 1).zfill(3))
                tmp_contour = '{}.shp'.format(geoserver_contour_file_name)

                self.flopy_model.sr.export_array_contours(tmp_contour, hdslayer)

                proj = flopy.utils.reference.getprj(self.flopy_model.sr.epsg)

                with open('{}.prj'.format(geoserver_contour_file_name), 'w') as f:
                    f.write(proj)

                geoserver_store = "{}:{}".format(self.WORKSPACE, geoserver_contour_file_name)

                geoserver_engine.create_shapefile_resource(geoserver_store,
                                                           overwrite=True,
                                                           shapefile_base=geoserver_contour_file_name)

                default_style = self.get_unique_item_name(self.VL_HEAD_CONTOUR)

                self.gs_engine.update_layer(layer_id=geoserver_store,
                                            default_style=default_style)

                os.remove(tmp_contour)
                # Deletes the shx and dbf files
                os.remove("{}.shx".format(geoserver_contour_file_name))
                os.remove("{}.dbf".format(geoserver_contour_file_name))
                os.remove("{}.prj".format(geoserver_contour_file_name))

    @reload_config()
    def delete_head_contour_layer(self, reload_config=True):
        """
        Deletes the head contour resource.

        Args:
            reload_config(bool): Reload the GeoServer node configuration and catalog before returning if True
        """
        hds = self.get_head_data()

        if hds is not None:
            geoserver_engine = self.gs_engine
            for i, hdslayer in enumerate(hds):
                contour_name = self.get_unique_item_name(self.VL_HEAD_CONTOUR, model_file_db=self.model_file_db)
                geoserver_contour_file_name = '{}_{}'.format(contour_name, str(i + 1).zfill(3))
                geoserver_store = "{}:{}".format(self.WORKSPACE, geoserver_contour_file_name)
                geoserver_engine.delete_resource(geoserver_store)

    @reload_config()
    def create_all_vector_layers(self, reload_config=True):
        """
        High level method to create all GeoServer vector layers.

        Args:
            reload_config(bool): Reload the GeoServer node configuration and catalog before returning if True.
        """

        # Boundary
        self.create_model_boundary_layer(
            reload_config=False
        )

    @reload_config()
    def delete_all_vector_layers(self, reload_config=True):
        """
        High level method to create all GeoServer vector layers.

        Args:
            reload_config(bool): Reload the GeoServer node configuration and catalog before returning if True.
        """

        # Boundary
        self.delete_model_boundary_layer(
            reload_config=False
        )

    @reload_config()
    def create_all_raster_layers(self, reload_config=True):
        """
        High level method to create all GeoServer raster layers.

        Args:
            reload_config(bool): Reload the GeoServer node configuration and catalog before returning if True.
        """
        # Head
        self.create_head_raster_layer(
            reload_config=False
        )

        # Packages
        self.create_package_shapefile_layers(
            reload_config=False
        )

    @reload_config()
    def delete_all_raster_layers(self, reload_config=True):
        """
        High level method to create all GeoServer raster layers.

        Args:
            reload_config(bool): Reload the GeoServer node configuration and catalog before returning if True.
        """
        # Head Raster
        self.delete_head_raster_layer(
            reload_config=False
        )

        # Packages
        self.delete_package_shapefile_layers(
            reload_config=False
        )

    @reload_config()
    def create_all_layers(self, reload_config=True):
        """
        High level function to create all GeoServer layers for the modflow project.

        Args:
            reload_config(bool): Reload the GeoServer node configuration and catalog before returning if True.
        """
        print("Printing All Layers")
        # Vector
        self.create_all_vector_layers(
            reload_config=False
        )

        # Raster
        self.create_all_raster_layers(
            reload_config=False
        )

    @reload_config()
    def delete_all_layers(self, reload_config=True):
        """
        High level function to delete all GeoServer layers for the modflow project.

        Args:
            reload_config(bool): Reload the GeoServer node configuration and catalog before returning if True.
        """
        # Vector
        self.delete_all_vector_layers(
            reload_config=False
        )
        # Raster
        self.delete_all_raster_layers(
            reload_config=False
        )

    @reload_config()
    def create_all_styles(self, overwrite=True, reload_config=True):
        """
        High level function to create all GeoServer styles for the modflow project.

        Args:
            overwrite(bool): Overwrite style if already exists when True. Defaults to False.
            reload_config(bool): Reload the GeoServer node configuration and catalog before returning if True.
        """

        # Head Raster
        self.create_raster_style(
            overwrite=overwrite,
            reload_config=False
        )

        # Model Boundary
        self.create_model_boundary_style(
            overwrite=overwrite,
            reload_config=False
        )

        # Model Grid
        self.create_model_grid_style(
            overwrite=overwrite,
            reload_config=False
        )

    @reload_config()
    def delete_all_styles(self, purge=True, reload_config=True):
        """
        High level function to delete all GeoServer styles for the modflow project.

        Args:
            purge(bool): Force remove all resources associated with style.
            reload_config(bool): Reload the GeoServer node configuration and catalog before returning if True.
        """

        # Raster
        self.delete_raster_style(
            purge=purge,
            reload_config=False
        )

        # Model Boundary
        self.delete_model_boundary_style(
            purge=purge,
            reload_config=False
        )

    @reload_config()
    def create_all(self, reload_config=True):
        """
        High level function to create all layers and styles for the modflow project.

        Args:
            reload_config(bool): Reload the GeoServer node configuration and catalog before returning if True.
        """
        self.create_all_layers(reload_config=False)

    @reload_config()
    def get_all_boundary_layers(self, app, reload_config=True):
        """
        Get all the layers in the model_boundary layer group on geoserver.

        Args:
            reload_config(bool): Reload the GeoServer node configuration and catalog before returning if True.
        Returns:
            layers (list): List of layer in the model boundary layer group
            bounds (list): minx, miny, maxx, maxy
        """
        boundary_layers = []
        Session = app.get_persistent_store_database('primary_db', as_sessionmaker=True)
        session = Session()

        # Get resource_id and name by querying the resource with database_id
        resources = session.query(ModflowModelResource).all()
        for resource in resources:
            attributes = json.loads(resource._attributes)
            db_id = attributes['database_id'].replace("_", "-")
            boundary_layers.append("{}:{}-{}_{}".format(self.WORKSPACE, self.WORKSPACE, db_id, self.VL_MODEL_BOUNDARY))

        minx = app.get_custom_setting('minx_extent')
        miny = app.get_custom_setting('miny_extent')
        maxx = app.get_custom_setting('maxx_extent')
        maxy = app.get_custom_setting('maxy_extent')
        bounds = [float(minx), float(miny), float(maxx), float(maxy)]

        return boundary_layers, bounds

    @staticmethod
    def compress_array(array, ibound_layer):
        mask_array = np.ma.masked_where(ibound_layer == 0, array)
        compress_mask_array = np.ma.compressed(mask_array)
        return compress_mask_array

    def crop_reproject_raster(self, new_projection, in_raster_file, out_raster_file):
        tmp_raster2 = 'raster_temp2.tif'
        if not self._boundary:
            self.load_boundary()
        data = rasterio.open(in_raster_file)
        out_img, out_transform = mask(dataset=data, shapes=[mapping(self._boundary)], crop=True)
        out_meta = data.meta.copy()
        out_meta.update({"height": out_img.shape[1],
                         "width": out_img.shape[2],
                         "transform": out_transform,
                         "crs": data.meta['crs']})
        # out_img[out_img == -9999] = np.nan
        with rasterio.open(tmp_raster2, 'w', **out_meta) as src_temp:
            src_temp.write(out_img)
        # Reproject file to Mercator 3857 so geoserver doesn't have to reproject on the fly
        with rasterio.open(tmp_raster2, 'w', **out_meta) as src:
            transform_info, width_info, height_info = calculate_default_transform(src.crs, new_projection, src.width,
                                                                                  src.height, *src.bounds)
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': new_projection,
                'transform': transform_info,
                'width': width_info,
                'height': height_info,
            })

            with rasterio.open(out_raster_file, 'w', **kwargs) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform_info,
                        dst_crs=new_projection,
                        repsampling=Resampling.nearest,
                    )
                dst.write(out_img)

    def crop_raster(self, in_raster_file, out_raster_file):
        if not self._boundary:
            self.load_boundary()
        data = rasterio.open(in_raster_file)
        out_img, out_transform = mask(dataset=data, shapes=[mapping(self._boundary)], crop=True)
        out_meta = data.meta.copy()
        out_meta.update({"height": out_img.shape[1],
                         "width": out_img.shape[2],
                         "transform": out_transform,
                         "crs": data.meta['crs']})

        with rasterio.open(out_raster_file, 'w', **out_meta) as src:
            src.write(out_img)

    @staticmethod
    def get_min_max_non_zeros(arr):
        if arr.min() == 0 and arr.max() == 0:
            minval = 0
            maxval = 0
        else:
            minval = np.min(arr[np.nonzero(arr)])
            maxval = np.max(arr[np.nonzero(arr)])
        return minval, maxval
