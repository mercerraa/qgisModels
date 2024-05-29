"""
Model exported as python.
Name : Attribute Centroid (buffer)
Group : 
With QGIS : 33602
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterPoint
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterField
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsProcessingParameterFeatureSink
import processing


class AttributeCentroidBuffer(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        # Click on button to search in map
        self.addParameter(QgsProcessingParameterPoint('point_in', 'Point In', defaultValue='0,0'))
        self.addParameter(QgsProcessingParameterNumber('distance', 'Distance', type=QgsProcessingParameterNumber.Double, minValue=1, defaultValue=10000))
        self.addParameter(QgsProcessingParameterVectorLayer('selectfromvector', 'SelectFromVector', types=[QgsProcessing.TypeVectorAnyGeometry], defaultValue=None))
        self.addParameter(QgsProcessingParameterField('field', 'Field', type=QgsProcessingParameterField.String, parentLayerParameterName='selectfromvector', allowMultiple=False, defaultValue='Field Name'))
        # This tool uses regex to search through text. To exemplify how the list below will be used.
        # 
        # --------------------------
        # myWord
        # Myword
        # myword
        # MYWORD
        # name 12:1
        # name 12
        # other 12:1
        # other 12
        # ---------------------------
        # 
        # Regex is case sensitive, which means that "myWord" is not the same as "myword" or any of the other variants listed.
        # To search for "myWord" simply write in the box: 
        # 
        # myWord
        # 
        # To search for any variant of myword you must tell regex to search insensitive to case:
        # 
        # (?i)myword  
        # 
        # which would return true for all four.
        # 
        # To specify some letters and some numbers plus a colon in a particular order:
        # 
        # [a-zA-Z]+ \d+:
        # 
        # would return true for "name 12:1" and "other 12:1". In this regex search only the colon is given explicitly.
        # The part "[a-zA-Z]+ " means search for a string of letters, both lowercase or uppercase, followed by a space.
        # The part "\d+" means search for a string of numbers. This is followed directly by the colon.
        # 
        self.addParameter(QgsProcessingParameterString('search_term', 'Search Term', multiLine=False, defaultValue='(?i)WORD'))
        self.addParameter(QgsProcessingParameterFeatureSink('Withinbuffer', 'WithinBuffer', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, supportsAppend=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Withinbufferwithattribute', 'WithinBufferWithAttribute', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, supportsAppend=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Matchingattributes', 'MatchingAttributes', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, supportsAppend=True, defaultValue='TEMPORARY_OUTPUT'))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(13, model_feedback)
        results = {}
        outputs = {}

        # Set Search Word
        alg_params = {
            'NAME': 'SearchWord',
            'VALUE': parameters['search_term']
        }
        outputs['SetSearchWord'] = processing.run('native:setprojectvariable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Set Search Field
        alg_params = {
            'NAME': 'SearchField',
            'VALUE': parameters['field']
        }
        outputs['SetSearchField'] = processing.run('native:setprojectvariable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Create layer from point
        alg_params = {
            'INPUT': parameters['point_in'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CreateLayerFromPoint'] = processing.run('native:pointtolayer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Reproject layer
        alg_params = {
            'CONVERT_CURVED_GEOMETRIES': False,
            'INPUT': outputs['CreateLayerFromPoint']['OUTPUT'],
            'OPERATION': None,
            'TARGET_CRS': 'ProjectCrs',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ReprojectLayer'] = processing.run('native:reprojectlayer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Create spatial index
        alg_params = {
            'INPUT': outputs['ReprojectLayer']['OUTPUT']
        }
        outputs['CreateSpatialIndex'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Extract within distance
        alg_params = {
            'DISTANCE': parameters['distance'],
            'INPUT': parameters['selectfromvector'],
            'REFERENCE': outputs['CreateSpatialIndex']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractWithinDistance'] = processing.run('native:extractwithindistance', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # BufferedCount
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'BufferedCount',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,  # Integer (32 bit)
            'FORMULA': ' count( "fid")',
            'INPUT': outputs['ExtractWithinDistance']['OUTPUT'],
            'OUTPUT': parameters['Withinbuffer']
        }
        outputs['Bufferedcount'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Withinbuffer'] = outputs['Bufferedcount']['OUTPUT']

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # Extract by expression
        alg_params = {
            'EXPRESSION': 'attribute(@SearchField) ~ @SearchWord',
            'INPUT': outputs['Bufferedcount']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractByExpression'] = processing.run('native:extractbyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # AttributeCount
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'AttributeCount',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,  # Integer (32 bit)
            'FORMULA': ' count( "fid")',
            'INPUT': outputs['ExtractByExpression']['OUTPUT'],
            'OUTPUT': parameters['Withinbufferwithattribute']
        }
        outputs['Attributecount'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Withinbufferwithattribute'] = outputs['Attributecount']['OUTPUT']

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # Collect geometries
        alg_params = {
            'FIELD': [''],
            'INPUT': outputs['Attributecount']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CollectGeometries'] = processing.run('native:collect', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(10)
        if feedback.isCanceled():
            return {}

        # Fix geometries
        alg_params = {
            'INPUT': outputs['CollectGeometries']['OUTPUT'],
            'METHOD': 1,  # Structure
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FixGeometries'] = processing.run('native:fixgeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(11)
        if feedback.isCanceled():
            return {}

        # Centroids
        alg_params = {
            'ALL_PARTS': False,
            'INPUT': outputs['FixGeometries']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Centroids'] = processing.run('native:centroids', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(12)
        if feedback.isCanceled():
            return {}

        # Retain fields
        alg_params = {
            'FIELDS': ['BufferedCount','AttributeCount'],
            'INPUT': outputs['Centroids']['OUTPUT'],
            'OUTPUT': parameters['Matchingattributes']
        }
        outputs['RetainFields'] = processing.run('native:retainfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Matchingattributes'] = outputs['RetainFields']['OUTPUT']
        return results

    def name(self):
        return 'Attribute Centroid (buffer)'

    def displayName(self):
        return 'Attribute Centroid (buffer)'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def shortHelpString(self):
        return """<html><body><p><!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
<html><head><meta name="qrichtext" content="1" /><style type="text/css">
p, li { white-space: pre-wrap; }
</style></head><body style=" font-family:'MS Shell Dlg 2'; font-size:8.3pt; font-weight:400; font-style:normal;">
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">Set a centre point and distance for a selection buffer, then select using a keyword/phrase in an attribute field of a chosen vector layer.</p>
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">The tool will then return a layer containing the objects within the buffer, a layer containing those objects within the buffer and that fulfill the attribute selection criteria and a layer containg a centroid of those objects.</p></body></html></p>
<h2>Input parameters</h2>
<h3>Point In</h3>
<p>Either manually enter Northing, Easting or click on the button to the right to click on a position in the map window.</p>
<h3>Distance</h3>
<p>Distance around "Point In" in metres. These two together define the buffer.</p>
<h3>SelectFromVector</h3>
<p>The vector layer to be selected from</p>
<h3>Field</h3>
<p>The attribute field to search through</p>
<h3>Search Term</h3>
<p>This tool uses regex to search through text. To exemplify how the list below will be used.
 
 --------------------------
 myWord
 Myword
 myword
 MYWORD
 name 12:1
 name 12
 other 12:1
 other 12
 ---------------------------
 
 Regex is case sensitive, which means that "myWord" is not the same as "myword" or any of the other variants listed.
 To search for "myWord" simply write in the box: 
 
 myWord
 
 To search for any variant of myword you must tell regex to search insensitive to case:
 
 (?i)myword  
 
 which would return true for all four.
 
 To specify some letters and some numbers plus a colon in a particular order:
 
 [a-zA-Z]+ \d+:
 
 would return true for "name 12:1" and "other 12:1". In this regex search only the colon is given explicitly.
 The part "[a-zA-Z]+ " means search for a string of letters, both lowercase or uppercase, followed by a space.
 The part "\d+" means search for a string of numbers. This is followed directly by the colon.</p>
<h2>Outputs</h2>
<h3>WithinBuffer</h3>
<p>Those objects found within the set buffer.</p>
<h3>WithinBufferWithAttribute</h3>
<p>Those objects found within the set buffer also matching the attribute selection crieria.</p>
<h3>MatchingAttributes</h3>
<p>The centroid of the matching objects. </p>
<h2>Examples</h2>
<p><!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
<html><head><meta name="qrichtext" content="1" /><style type="text/css">
p, li { white-space: pre-wrap; }
</style></head><body style=" font-family:'MS Shell Dlg 2'; font-size:8.3pt; font-weight:400; font-style:normal;">
<p style="-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><br /></p></body></html></p><br><p align="right">Algorithm author: Andrew Mercer (mercerraa@gmail.com)</p></body></html>"""

    def createInstance(self):
        return AttributeCentroidBuffer()
