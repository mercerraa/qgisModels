"""
Name : Byggnad2Fastighet_v3
With QGIS : 33602
Andrew Mercer, 10.06.2024
This model is designed for a specific use case and not for general usage.
Usage is free but almost certainly of limited use.
It requires vector layers (1 point and 2 polygon).
The model takes points representing builings, which are not alwyas located 
within the actual building's geometry, and tries to match these to polygons
representing the same building and then transfers attributes from the points to 
cadastral parcels under the assumption that the building polygon
is correctly placed.
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingParameterField
from qgis.core import QgsProcessingUtils
import processing
from qgis.core import (
    QgsFields,
    QgsField,
    QgsFeature,
    QgsFeatureSink,
    QgsProject,
    NULL,
    QgsGeometry,
    QgsPalLayerSettings,
    QgsTextFormat,
    QgsTextBackgroundSettings,
    QgsVectorLayerSimpleLabeling
)
from qgis.PyQt.QtCore import (
    QVariant
)
from PyQt5.QtGui import QFont, QColor
from qgis.utils import iface

class Byggfast(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        layers_names = [layer.name() for layer in QgsProject.instance().mapLayers().values()]
        byggPointLayer = None
        byggFieldsDefault = None
        byggPolygonLayer = None
        fastPolygonLayer = None
        fastFieldsDefault = None
        for i in range(len(layers_names)):
            if 'byggnader_sverige_point' in layers_names[i]: 
                byggPointLayer = layers_names[i]
                byggFieldsDefault = ['id', 'anlaggning_id', 'fastighetsnyckel', 'fast_byg_uuid', 'byggnadsbeteckning', 'visningsurl']
            if 'by_' in layers_names[i]: 
                byggPolygonLayer =layers_names[i]
            if 'ay_' in layers_names[i]: 
                fastPolygonLayer =layers_names[i]
                fastFieldsDefault = ['FNR_FDS', 'OBJEKT_ID', 'KOMMUNNAMN', 'FASTIGHET']
            
        
        self.addParameter(QgsProcessingParameterVectorLayer('byggnaderpoints', 'ByggnaderPoints', types=[QgsProcessing.TypeVectorPoint], defaultValue=byggPointLayer))
        self.addParameter(QgsProcessingParameterField('byggnadfields', 'ByggnadFields', type=QgsProcessingParameterField.Any, parentLayerParameterName='byggnadpoints', allowMultiple=True, defaultValue=byggFieldsDefault))
        self.addParameter(QgsProcessingParameterVectorLayer('byggnaderpolygons', 'ByggnaderPolygons', types=[QgsProcessing.TypeVectorPolygon], defaultValue=byggPolygonLayer))
        self.addParameter(QgsProcessingParameterVectorLayer('fastigheterpolygons', 'FastigheterPolygons', types=[QgsProcessing.TypeVectorPolygon], defaultValue=fastPolygonLayer))
        self.addParameter(QgsProcessingParameterField('fastighetfields', 'FastighetFields', type=QgsProcessingParameterField.Any, parentLayerParameterName='fastigheterpolygon', allowMultiple=True, defaultValue=fastFieldsDefault))
        #self.addParameter(QgsProcessingParameterFeatureSink('SnapGeometriesToLayer', 'SnapGeometriesToLayer', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))
        #self.addParameter(QgsProcessingParameterFeatureSink('Intersection', 'Intersection', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))
        #self.addParameter(QgsProcessingParameterFeatureSink('Centroids', 'Centroids', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))
        #self.addParameter(QgsProcessingParameterFeatureSink('Extractbylocation', 'ExtractByLocation', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('BMFastighet', 'BM Fastigheter', optional=True, type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(14, model_feedback)
        results = {}
        outputs = {}

        # Create spatial index
        alg_params = {
            'INPUT': parameters['byggnaderpoints']
        }
        outputs['CreateSpatialIndex'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Create spatial index
        alg_params = {
            'INPUT': parameters['byggnaderpolygons']
        }
        outputs['CreateSpatialIndex'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Create spatial index
        alg_params = {
            'INPUT': parameters['fastigheterpolygons']
        }
        outputs['CreateSpatialIndex'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Disjoint
        print("run Disjoint")
        alg_params = {
            'INPUT': parameters['byggnaderpoints'],
            'INTERSECT': parameters['byggnaderpolygons'],
            'PREDICATE': [2],  # disjoint
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Disjoint'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Intersect
        print("run Intersect")
        alg_params = {
            'INPUT': parameters['byggnaderpoints'],
            'INTERSECT': parameters['byggnaderpolygons'],
            'PREDICATE': [0],  # intersect
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Intersect'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Snap geometries to layer
        print("run Snap geometries")
        alg_params = {
            'BEHAVIOR': 3,  # Prefer closest point, don't insert new vertices
            'INPUT': outputs['Disjoint']['OUTPUT'], #parameters['byggnadpoints'],
            'REFERENCE_LAYER': parameters['byggnaderpolygons'],
            'TOLERANCE': 50,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT #parameters['SnapGeometriesToLayer']
        }
        outputs['SnapGeometriesToLayer'] = processing.run('native:snapgeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        #results['SnapGeometriesToLayer'] = outputs['SnapGeometriesToLayer']['OUTPUT']

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Buffer
        print("run Buffer")
        alg_params = {
            'DISSOLVE': False,
            'DISTANCE': 0.1,
            'END_CAP_STYLE': 0,  # Round
            'INPUT': outputs['SnapGeometriesToLayer']['OUTPUT'],
            'JOIN_STYLE': 0,  # Round
            'MITER_LIMIT': 2,
            'SEGMENTS': 5,
            'SEPARATE_DISJOINT': False,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Buffer'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # Intersection
        print("run Intersection")
        alg_params = {
            'GRID_SIZE': None,
            'INPUT': parameters['byggnaderpolygons'],
            'INPUT_FIELDS': ['fid'],
            'OVERLAY': outputs['Buffer']['OUTPUT'],
            'OVERLAY_FIELDS': parameters['byggnadfields'],#['id','anlaggning_id','fastighetsnyckel','fast_byg_uuid','byggnadsbeteckning','visningsurl'],
            'OVERLAY_FIELDS_PREFIX': None,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT #parameters['Intersection']
        }
        outputs['Intersection'] = processing.run('native:intersection', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        #results['Intersection'] = outputs['Intersection']['OUTPUT']
        
        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}


        # Centroids
        print("run Centroids")
        alg_params = {
            'ALL_PARTS': False,
            'INPUT': outputs['Intersection']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT #parameters['Centroids']
        }
        outputs['Centroids'] = processing.run('native:centroids', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        #results['Centroids'] = outputs['Centroids']['OUTPUT']

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # Create spatial index
        print("run Spatial Index of Centroids")
        alg_params = {
            'INPUT': outputs['Centroids']['OUTPUT']
        }
        outputs['CreateSpatialIndex'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(10)
        if feedback.isCanceled():
            return {}
            
        # Merge vector layers
        print("run Merge Point Vectors")
        alg_params = {
            'CRS': 'ProjectCrs',
            'LAYERS': [outputs['Centroids']['OUTPUT'],outputs['Intersect']['OUTPUT']],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['remergePoints'] = processing.run('native:mergevectorlayers', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(11)
        if feedback.isCanceled():
            return {}
            
        # Extract by location
        print("run Extract by location Fastigheter and merged Byggnad Points")
        alg_params = {
            'INPUT': parameters['fastigheterpolygons'],
            'INTERSECT': outputs['remergePoints']['OUTPUT'],
            'PREDICATE': [0],  # intersect
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT #parameters['Extractbylocation']
        }
        outputs['ExtractByLocation'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        #results['Extractbylocation'] = outputs['ExtractByLocation']['OUTPUT']

        feedback.setCurrentStep(12)
        if feedback.isCanceled():
            return {}

        # Create spatial index
        print("run Spatial Index")
        alg_params = {
            'INPUT': outputs['ExtractByLocation']['OUTPUT']
        }
        outputs['CreateSpatialIndex'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(13)
        if feedback.isCanceled():
            return {}
            
        
        #######################################################################################################  
        # Fetch the feature "layers" for fastigheter and byggnader. These are so called iterators and must be converted to lists of features otherwise Python shit happens.
        print("run My code")
        features_fastigheter = list(context.temporaryLayerStore().mapLayers()[outputs['ExtractByLocation']['OUTPUT']].getFeatures())
        features_byggnader_del1 = list(context.temporaryLayerStore().mapLayers()[outputs['Centroids']['OUTPUT']].getFeatures())
        features_byggnader_del2 = list(context.temporaryLayerStore().mapLayers()[outputs['Intersect']['OUTPUT']].getFeatures())
        features_byggnader = features_byggnader_del1 + features_byggnader_del2
        
        source = self.parameterAsSource(
            parameters,
            'fastigheterpolygons',
            context
        )
        
        # Create attribute fields for the new layer 
        newFields = QgsFields()  
        #fastighetAttributeNameList = ['FNR_FDS', 'OBJEKT_ID', 'KOMMUNKOD', 'FASTIGHET']
        fastighetAttributeNameList = parameters['fastighetfields']
        for i in range(len(fastighetAttributeNameList)):
            newFields.append(QgsField(fastighetAttributeNameList[i], QVariant.String))
        newFields.append(QgsField('AntalByggnader', QVariant.Int))

        #byggnadAttributeNameList = ['id', 'anlaggning_id', 'fastighetsnyckel', 'fast_byg_uuid', 'byggnadsbeteckning', 'visningsurl']
        byggnadAttributeNameList = parameters['byggnadfields']
        for j in range(len(byggnadAttributeNameList)):
            newFields.append(QgsField(byggnadAttributeNameList[j], QVariant.String))
        
        # Loop through "fastigheter" features
        print("run Loop through 'fastigheter' features")
        spacer ='; '
        fastighetCount = 0
        for feature_fastighet in features_fastigheter:
            fastighet_geometry = feature_fastighet.geometry()
            fastighet_geometry_engine = QgsGeometry.createGeometryEngine(fastighet_geometry.constGet()) # QgsGeometryEngine should speed up intersect
            fastighet_geometry_engine.prepareGeometry()
            # Loop through "byggnader" features. has_building keeps track of i) if a fastighet is associated with a byggnad and how many
            has_building = 0
            for feature_byggnad in features_byggnader:
                # Is the building within the property boundary? If "yes" check building count, if this is first building for this property cretae a new feature from the property
                #if fastighet_geometry.contains(feature_byggnad.geometry()):
                if fastighet_geometry_engine.intersects(feature_byggnad.geometry().constGet()):
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
                        'BMFastighet',
                        context, newFields, source.wkbType(), source.sourceCrs()
                    )
        
                sink.addFeature(newFeature, QgsFeatureSink.FastInsert)
                
                results['BMFastighet'] = dest_id
        
        vlayer = QgsProcessingUtils.mapLayerFromString(results['BMFastighet'], context)
        vlayer.renderer().symbol().setColor(QColor(150,150,250))
        vlayer.triggerRepaint()
        label_settings = QgsPalLayerSettings()
        #label_settings.drawBackground = True
        label_settings.fieldName = 'AntalByggnader'

        text_format = QgsTextFormat()
        background_color = QgsTextBackgroundSettings()
        background_color.setFillColor(QColor(200,200,255))
        background_color.setEnabled(True)
        text_format.setBackground(background_color )
        label_settings.setFormat(text_format)

        vlayer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
        vlayer.setLabelsEnabled(True)
        vlayer.triggerRepaint()
        iface.layerTreeView().refreshLayerSymbology(vlayer.id())
        ########################################################################################################
        
        return results

    def name(self):
        return 'Byggnad2Fastighet_v3'

    def displayName(self):
        return 'Byggnad2Fastighet_v3'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return Byggfast()
