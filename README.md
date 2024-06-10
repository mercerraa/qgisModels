# qgisModels
Models for QGIS Processing toolbox

## File types

There are two "types" of model available in the QGIS processing toolbox: .model3 and .py
The first is an xml file that is generally constructed using the model designer tool, that is to say graphically.
The second is a python script that calls tools and GUI elements from the processing toolbox framework.

The two types are/can be stored in seperate locations within a user's QGIS profile.
The location of the "profiles" folder differs between operating systems [(QGIS website details)](https://plugins.qgis.org/planet/tag/qgis3/ ).
Once in "QGIS3/profiles/my_user_name/" (where my_user_name is the profile name you are using in QGS) you will see a folder titled "processing".
In this folder there are two subfolders: "models" is used for the .model3 files and "scripts" is used for the .py files.
Files placed in these folders will be available in the processing toolbox.
Processing models created in QGIS will be stored in these locations.

## Contents

- AttrbCent creates a centroid for selected attributes of a vector layer.
- AttrbCent_buff does the same but the user can preselect a geographical subset using a point buffer designated withing the tool.
- Byggnad2Fastighet is a tool designed for a specific use within RAÄ. It attempts to place a building point within its associated cadastral unit.
  - This sounds simple enough but really isn't