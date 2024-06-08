"""
Model exported as python.
Name : ByggFast_v2
Group : 
With QGIS : 33602
Andrew Mercer, 08.06.2024
This model is designed for a specific use case and not for general usage.
It requires vector layers (1 point and 2 polygon) with specific field names.
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterFeatureSink
import processing
from qgis.core import (
    QgsFields,
    QgsField,
    QgsFeature,
    QgsFeatureSink,
    QgsProject,
    NULL
)
from qgis.PyQt.QtCore import QVariant

class Byggfast(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        layers_names = [layer.name() for layer in QgsProject.instance().mapLayers().values()]
        byggPointLayer = None
        byggPolygonLayer = None
        fastPolygonLayer = None
        for i in range(len(layers_names)):
            if 'byggnader_sverige_point' in layers_names[i]: 
                byggPointLayer = layers_names[i]
            if 'by_' in layers_names[i]: 
                byggPolygonLayer =layers_names[i]
            if 'ay_' in layers_names[i]: 
                fastPolygonLayer =layers_names[i]
                
        self.addParameter(QgsProcessingParameterVectorLayer('byggnadpoints', 'ByggnadPoints', types=[QgsProcessing.TypeVectorPoint], defaultValue=byggPointLayer))
        self.addParameter(QgsProcessingParameterVectorLayer('byggnaderpolygon', 'ByggnaderPolygon', types=[QgsProcessing.TypeVectorPolygon], defaultValue=byggPolygonLayer))
        self.addParameter(QgsProcessingParameterVectorLayer('fastigheterpolygon', 'FastigheterPolygon', types=[QgsProcessing.TypeVectorPolygon], defaultValue=fastPolygonLayer))
        self.addParameter(QgsProcessingParameterFeatureSink('Extractbylocation', 'ExtractByLocation', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Joined', 'Joined', optional=True, type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(14, model_feedback)
        results = {}
        outputs = {}

        # Create spatial index
        alg_params = {
            'INPUT': parameters['byggnadpoints']
        }
        outputs['CreateSpatialIndex'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Create spatial index
        alg_params = {
            'INPUT': parameters['byggnaderpolygon']
        }
        outputs['CreateSpatialIndex'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Create spatial index
        alg_params = {
            'INPUT': parameters['fastigheterpolygon']
        }
        outputs['CreateSpatialIndex'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Snap geometries to layer
        alg_params = {
            'BEHAVIOR': 3,  # Prefer closest point, don't insert new vertices
            'INPUT': parameters['byggnadpoints'],
            'REFERENCE_LAYER': parameters['byggnaderpolygon'],
            'TOLERANCE': 50,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['SnapGeometriesToLayer'] = processing.run('native:snapgeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Buffer
        alg_params = {
            'DISSOLVE': False,
            'DISTANCE': 2,
            'END_CAP_STYLE': 0,  # Round
            'INPUT': outputs['SnapGeometriesToLayer']['OUTPUT'],
            'JOIN_STYLE': 0,  # Round
            'MITER_LIMIT': 2,
            'SEGMENTS': 5,
            'SEPARATE_DISJOINT': False,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Buffer'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Create spatial index
        alg_params = {
            'INPUT': outputs['Buffer']['OUTPUT']
        }
        outputs['CreateSpatialIndex'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Intersection
        alg_params = {
            'GRID_SIZE': None,
            'INPUT': parameters['byggnaderpolygon'],
            'INPUT_FIELDS': ['fid'],
            'OVERLAY': outputs['Buffer']['OUTPUT'],
            'OVERLAY_FIELDS': ['id','anlaggning_id','fastighetsnyckel','fast_byg_uuid','byggnadsbeteckning','visningsurl'],
            'OVERLAY_FIELDS_PREFIX': None,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Intersection'] = processing.run('native:intersection', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # Create spatial index
        alg_params = {
            'INPUT': outputs['Intersection']['OUTPUT']
        }
        outputs['CreateSpatialIndex'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # Centroids
        alg_params = {
            'ALL_PARTS': False,
            'INPUT': outputs['Intersection']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Centroids'] = processing.run('native:centroids', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # Create spatial index
        alg_params = {
            'INPUT': outputs['Centroids']['OUTPUT']
        }
        outputs['CreateSpatialIndex'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(10)
        if feedback.isCanceled():
            return {}

        # Extract by location
        alg_params = {
            'INPUT': parameters['fastigheterpolygon'],
            'INTERSECT': outputs['Centroids']['OUTPUT'],
            'PREDICATE': [0],  # intersect
            'OUTPUT': parameters['Extractbylocation']
        }
        outputs['ExtractByLocation'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Extractbylocation'] = outputs['ExtractByLocation']['OUTPUT']

        feedback.setCurrentStep(11)
        if feedback.isCanceled():
            return {}

        # Create spatial index
        alg_params = {
            'INPUT': outputs['ExtractByLocation']['OUTPUT']
        }
        outputs['CreateSpatialIndex'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(12)
        if feedback.isCanceled():
            return {}
            
        
        #######################################################################################################  
        # Fetch the feature "layers" for fastigheter and byggnader. These are so called iterators and must be converted to lists of features otherwise Python shit happens.
        features_fastigheter = list(context.temporaryLayerStore().mapLayers()[outputs['ExtractByLocation']['OUTPUT']].getFeatures())
        features_byggnader = list(context.temporaryLayerStore().mapLayers()[outputs['Centroids']['OUTPUT']].getFeatures())
        
        source = self.parameterAsSource(
            parameters,
            'fastigheterpolygon',
            context
        )

        # Create attribute fields for the new layer 
        newFields = QgsFields()  
        fastighetAttributeNameList = ['FNR_FDS', 'OBJEKT_ID', 'KOMMUNKOD', 'FASTIGHET']
        for i in range(len(fastighetAttributeNameList)):
            newFields.append(QgsField(fastighetAttributeNameList[i], QVariant.String))
        newFields.append(QgsField('AntalByggnader', QVariant.Int))

        byggnadAttributeNameList = ['id', 'anlaggning_id', 'fastighetsnyckel', 'fast_byg_uuid', 'byggnadsbeteckning', 'visningsurl']
        for j in range(len(byggnadAttributeNameList)):
            newFields.append(QgsField(byggnadAttributeNameList[j], QVariant.String))
        
        # Loop through "fastigheter" features
        spacer ='; '
        fastighetCount = 0
        for feature_fastighet in features_fastigheter:
            fastighet_geometry = feature_fastighet.geometry()
            # Loop through "byggnader" features. has_building keeps track of i) if a fastighet is associated with a byggnad and how many
            has_building = 0
            for feature_byggnad in features_byggnader:
                # Is the building within the property boundary? If "yes" check building count, if this is first building for this property cretae a new feature from the property
                if fastighet_geometry.contains(feature_byggnad.geometry()):
                    has_building += 1
                    if has_building == 1:
                        fastighetCount += 1
                        newFeature = QgsFeature()
                        newFeature.setGeometry(fastighet_geometry)

                        fastighetAttributList = []
                        fastighet_attributes = feature_fastighet.attributes()
                        for name in fastighetAttributeNameList:
                            if fastighet_attributes[feature_fastighet.fields().indexFromName(name)] == NULL:
                                fastighetAttributList.append(None)
                            else:
                                fastighetAttributList.append(fastighet_attributes[feature_fastighet.fields().indexFromName(name)])

                        byggnadAttributList = ['']*len(byggnadAttributeNameList)
                        byggnadAttributeDict = dict(zip(byggnadAttributeNameList,byggnadAttributList))

                    byggnad_attributes = feature_byggnad.attributes()
                    for name in byggnadAttributeNameList:
                        if byggnad_attributes[feature_byggnad.fields().indexFromName(name)] == NULL:
                            attribute = 'Saknas'
                        else:
                            attribute = byggnad_attributes[feature_byggnad.fields().indexFromName(name)]
                        if has_building == 1:
                            byggnadAttributeDict[name]+=(attribute)
                        else:
                            byggnadAttributeDict[name]+=(spacer + attribute)
                    
            if has_building > 0:
                fastighetAttributList.append(has_building)
                attributeList = fastighetAttributList
                for name in byggnadAttributeNameList:
                        attributeList.append(byggnadAttributeDict[name])
                newFeature.setAttributes(attributeList)
                # Define feature layer to receive new features. This is weird in models and completely inconsistent with both plugins and console scripting
                if fastighetCount == 1:
                    (sink, dest_id) = self.parameterAsSink(
                        parameters,
                        'Joined',
                        context, newFields, source.wkbType(), source.sourceCrs()
                    )
        
                sink.addFeature(newFeature, QgsFeatureSink.FastInsert)
                
                results['Joined'] = dest_id
                
        ########################################################################################################
        
        
        return results

    def name(self):
        return 'Byggnad2Fastighet'

    def displayName(self):
        return 'Byggnad2Fastighet'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return Byggfast()
