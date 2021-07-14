"""
********************************************************************************
* Name: modflow_model_resource.py
* Author: ckrewson and mlebaron
* Created On: November 7, 2018
* Copyright: (c) Aquaveo 2018
********************************************************************************
"""
from tethysext.atcore.models.app_users import Resource

__all__ = ['ModflowModelResource']


class ModflowModelResource(Resource):
    """
    Resource models for Modflow models.
    """
    TYPE = 'modflow-model-resource'
    DISPLAY_TYPE_SINGULAR = 'Modflow Model'
    DISPLAY_TYPE_PLURAL = 'Modflow Models'

    UPLOAD_STATUS_KEY = 'upload'
    UPLOAD_GS_STATUS_KEY = 'upload_geoserver'

    # Polymorphism
    __mapper_args__ = {
        'polymorphic_identity': TYPE,
    }
