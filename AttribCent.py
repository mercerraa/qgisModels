"""
Model exported as python.
Name : AttributeCentroid
Group : 
With QGIS : 33602
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterField
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsProcessingParameterFeatureSink
import processing


class Attributecentroid(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
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
        self.addParameter(QgsProcessingParameterFeatureSink('Withattribute', 'WithAttribute', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, supportsAppend=True, defaultValue='TEMPORARY_OUTPUT'))
        self.addParameter(QgsProcessingParameterFeatureSink('Attributecentroid', 'AttributeCentroid', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, supportsAppend=True, defaultValue='TEMPORARY_OUTPUT'))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(9, model_feedback)
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

        # LayerTotal
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'TotalCount',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,  # Integer (32 bit)
            'FORMULA': ' count( "fid")',
            'INPUT': parameters['selectfromvector'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Layertotal'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Extract by expression
        alg_params = {
            'EXPRESSION': 'attribute(@SearchField) ~ @SearchWord',
            'INPUT': outputs['Layertotal']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractByExpression'] = processing.run('native:extractbyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
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
            'OUTPUT': parameters['Withattribute']
        }
        outputs['Attributecount'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Withattribute'] = outputs['Attributecount']['OUTPUT']

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Collect geometries
        alg_params = {
            'FIELD': [''],
            'INPUT': outputs['Attributecount']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CollectGeometries'] = processing.run('native:collect', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Fix geometries
        alg_params = {
            'INPUT': outputs['CollectGeometries']['OUTPUT'],
            'METHOD': 1,  # Structure
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FixGeometries'] = processing.run('native:fixgeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # Centroids
        alg_params = {
            'ALL_PARTS': False,
            'INPUT': outputs['FixGeometries']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Centroids'] = processing.run('native:centroids', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # Retain fields
        alg_params = {
            'FIELDS': ['TotalCount','AttributeCount'],
            'INPUT': outputs['Centroids']['OUTPUT'],
            'OUTPUT': parameters['Attributecentroid']
        }
        outputs['RetainFields'] = processing.run('native:retainfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Attributecentroid'] = outputs['RetainFields']['OUTPUT']
        return results

    def name(self):
        return 'AttributeCentroid'

    def displayName(self):
        return 'AttributeCentroid'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def shortHelpString(self):
        return """<html><body><p><!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
<html><head><meta name="qrichtext" content="1" /><style type="text/css">
p, li { white-space: pre-wrap; }
</style></head><body style=" font-family:'MS Shell Dlg 2'; font-size:8.3pt; font-weight:400; font-style:normal;">
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">Select objects by search term in an attribute field. The tool then creates a layer containing those objects and a layer containg the centroid of those objects.</p></body></html></p>
<h2>Input parameters</h2>
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
<h3>AttributeCentroid</h3>
<p>The centroid point of the objects matching the selection criteria. The centroid has attributes for the total count of objects in the parent layer and a count of objects fulfilling the selection criteria.</p>
<h2>Examples</h2>
<p><!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
<html><head><meta name="qrichtext" content="1" /><style type="text/css">
p, li { white-space: pre-wrap; }
</style></head><body style=" font-family:'MS Shell Dlg 2'; font-size:8.3pt; font-weight:400; font-style:normal;">
<p style="-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><br /></p></body></html></p><br><p align="right">Algorithm author: Andrew Mercer (mercerraa@gmail.com)</p></body></html>"""

    def createInstance(self):
        return Attributecentroid()
