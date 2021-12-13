import arcpy
import os
import difflib


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "NBMGGeMSTools"
        self.alias = "NBMGGeMSTools"

        # List of tool classes associated with this toolbox
        self.tools = [fillGeMSLine, fillGeMSPoints, exportLinetoShpGeMS, exportPointtoShpGeMS,
                      exportPolygontoShpGeMS, fillGeMSPointsTesting, fillGeMSPointsTesting2]


class fillGeMSPoints(object):
    attributelist = ['LocationConfidenceMeters',
                     'IdentityConfidence',
                     'OrientationConfidenceDegrees',
                     'DataSourceID',
                     'LocationSourceID',
                     'OrientationSourceID',
                     'Display',
                     'PlotAtScale',
                     'Type']

    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Fill GeMS Points Attribute Table"
        self.description = "This tool fills in some GeMS related attributes given the value of Symbol. " \
                           "This tool will only autofill after both the geodatabase and a feature class are filled " \
                           "in. Note that the tool checks for which of these columns exist in the feature class during " \
                           "the validation phase, so ignore those attributes if not needed.\n If you " \
                           "don't want to edit certain Symbols, use the X next to the value table to delete those rows."
        self.canRunInBackground = False

    def getDomain(self, domains, domainname):
        return self.addBlankToDomain(next((domain for domain in domains if domain.name == domainname),
                                          None).codedValues)

    def addBlankToDomain(self, domain):
        domain['--'] = '--'
        return domain

    def getDomains(self, gdb, lyrname):
        global layerCV
        global confidenceCV
        global booleanCV
        global dataSourceCV
        global dictofdicts
        global locationConfidenceCV
        global scaleCV
        global typeCV

        domains = arcpy.da.ListDomains(gdb)

        layerCV = self.getDomain(domains, lyrname)
        confidenceCV = self.getDomain(domains, "Confidence")
        booleanCV = self.getDomain(domains, "Boolean")
        dataSourceCV = self.getDomain(domains, "DataSource")
        locationConfidenceCV = {'--': '--',
                                '5': '5',
                                '10': '10'}
        scaleCV = {'--': '--',
                   '2400':'2400',
                   '62500':'62500',
                   '50000':'50000',
                   '100000':'100000'}
        typeCV = self.getDomain(domains, "Type")
        dictofdicts = {'LocationConfidenceMeters': locationConfidenceCV,
                       'IdentityConfidence': confidenceCV,
                       'OrientationConfidenceDegrees': locationConfidenceCV,
                       'DataSourceID': dataSourceCV,
                       'LocationSourceID': dataSourceCV,
                       'OrientationSourceID': dataSourceCV,
                       'Display': booleanCV,
                       'PlotAtScale': scaleCV,
                       'Type': typeCV
                       }

    def getParameterInfo(self):
        geodatabase = arcpy.Parameter(
            displayName="Geodatabase",
            name="gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")

        param0 = arcpy.Parameter(
            displayName='Point Feature Class',
            name='in_features',
            datatype="GPFeatureLayer",
            parameterType='Required',
            direction='Input')

        param0.filter.list = ["Point"]

        param1 = arcpy.Parameter(
            displayName='GeMS Fields',
            name='gems_fields',
            datatype='GPValueTable',
            parameterType='Optional',
            direction='Input')

        param1.parameterDependencies = [param0.name]
        #param1.columns = [["String", "Symbol Code"],
        #                  ["String", "Symbol Name"],
        #                  ["String", "LocationConfidenceMeters"],
        #                 ["String", "IdentityConfidence"],
        #                 ["String", "OrientationConfidenceDegrees"],
        #                 ["String", "DataSourceID"],
        #                ["String", "LocationSourceID"],
        #                 ["String", "OrientationSourceID"],
        #                 ["String", "Display"],
        #                 ["String", "PlotAtScale"],
        #                 ]
        # param1.filters[1].typ

        #param1.filters[1].type = "ValueList"
        cols = [["String", "SymbolCode"],
                ["String", "Symbol Name"]]
        for att in fillGeMSPoints.attributelist: cols.append(["String", att])
        param1.columns = cols

        params = [geodatabase, param0, param1]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def unique_values(self, layer, field):
        with arcpy.da.SearchCursor(layer, field) as cursor:
            return sorted({row[0] for row in cursor})

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
                validation is performed.  This method is called whenever a parameter
                has been changed."""

        if parameters[1].altered and not parameters[1].hasBeenValidated\
                and parameters[0].altered:
            featurename = os.path.basename(str(parameters[1].value))
            self.getDomains(parameters[0].value, featurename)
            v_list = []
            symbol_values = self.unique_values(parameters[1].value, 'Symbol')
                #[f.name for f in arcpy.ListFields(parameters[0].value)]
            for symbol in symbol_values:
                if(featurename == "MapUnitPoints"):
                    v_list.append([symbol, symbol,
                                   '--', '--', '--', '--', '--', '--', '--', '--', '--'])
                else:
                    v_list.append([symbol, layerCV[symbol],
                                   '--', '--', '--', '--', '--', '--', '--', '--', '--'])
                del symbol
            parameters[2].value = v_list
            del symbol_values
            del v_list
            parameters[2].filters[2].list = locationConfidenceCV.values()
            parameters[2].filters[3].list = confidenceCV.values()
            parameters[2].filters[4].list = locationConfidenceCV.values()
            parameters[2].filters[5].list = dataSourceCV.values()
            parameters[2].filters[6].list = dataSourceCV.values()
            parameters[2].filters[7].list = dataSourceCV.values()
            parameters[2].filters[8].list = booleanCV.values()
            parameters[2].filters[9].list = scaleCV.values()
            parameters[2].filters[10].list = typeCV.values()

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def createFieldCalcFunction(self, param1, param2):
        return "def fillInField(Symbol, Param):\n    if Symbol == '"+param1+"':\n        return '"+param2+"'\n" \
                                                                                                   "    else:\n     " \
                                                                                                "return Param"

    def getDictKey(self, dictionary, value):
        return list(dictionary.keys())[list(dictionary.values()).index(value)]

    def execute(self, parameters, messages):
        fld_names = [f.name for f in arcpy.ListFields(parameters[1].value)]

        messages.addMessage(fillGeMSPoints.attributelist)
        messages.addMessage(fld_names)

        valuelist = parameters[2].value

        for row in valuelist:
            i = 0
            messages.addMessage("Changing values for " + row[1])
            for field in fillGeMSPoints.attributelist:
                if field not in fld_names:
                    messages.addMessage("skipping field " + field + ", not in feature layer")
                    i = i + 1
                    continue
                rownum = i + 2 #values start in column 3, index 2
                messages.addMessage(field + " = " + row[rownum])
                if (row[rownum] == '--'):
                    messages.addMessage("Skipping " + field + " for this row, value is '--'")
                else:
                    messages.addMessage(field + " = " + row[rownum])
                    fieldfunction = self.createFieldCalcFunction(row[0], self.getDictKey(dictofdicts.get(field),
                                                                                         row[rownum]))
                    code = 'fillInField(!Symbol!, !{}!)'.format(field)
                    arcpy.CalculateField_management(parameters[1].value, field,
                                                    code, 'PYTHON_9.3', fieldfunction)
                i = i + 1
        return


class fillGeMSLine(object):
    attributelist = ['IsConcealed',
                     'LocationConfidenceMeters',
                     'ExistenceConfidence',
                     'IdentityConfidence',
                     'Display',
                     'PolyBuilder',
                     'DataSourceID',
                     'Type']

    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Fill GeMS Lines Attribute Table"
        self.description = "This tool fills in some GeMS related attributes given the value of Symbol. " \
                           "This tool will only autofill after both the geodatabase and a feature class are filled " \
                           "in. Note that the tool checks for which of these columns exist in the feature class during " \
                           "the validation phase, so ignore those attributes if not needed.\n If you " \
                           "don't want to edit certain Symbols, use the X next to the value table to delete those rows."
        self.canRunInBackground = False

    def getDomain(self, domains, domainname):
        return self.addBlankToDomain(next((domain for domain in domains if domain.name == domainname),
                                            None).codedValues)

    def addBlankToDomain(self, domain):
        domain['--'] = '--'
        return domain

    def getDomains(self, gdb, lyrname):
        global layerCV
        global concealedCV
        global confidenceCV
        global booleanCV
        global dataSourceCV
        global typeCV
        global domains
        global dictofdicts
        global locationConfidenceCV

        domains = arcpy.da.ListDomains(gdb)

        layerCV = self.getDomain(domains, lyrname)
        concealedCV = self.getDomain(domains, "Concealed")
        confidenceCV = self.getDomain(domains, "Confidence")
        booleanCV = self.getDomain(domains, "Boolean")
        dataSourceCV = self.getDomain(domains, "DataSource")
        locationConfidenceCV = {'--': '--',
                                '5': '5',
                                '10': '10'}
        typeCV = self.getDomain(domains, "Type")
        dictofdicts = {'IsConcealed': concealedCV,
                       'LocationConfidenceMeters': locationConfidenceCV,
                       'ExistenceConfidence': confidenceCV,
                       'IdentityConfidence': confidenceCV,
                       'Display': booleanCV,
                       'PolyBuilder': booleanCV,
                       'DataSourceID': dataSourceCV,
                       'Type': typeCV}

    def getParameterInfo(self):
        geodatabase = arcpy.Parameter(
            displayName="Geodatabase:",
            name="gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")

        param0 = arcpy.Parameter(
            displayName='Feature Class',
            name='in_features',
            datatype="GPFeatureLayer",
            parameterType='Required',
            direction='Input')

        param0.filter.list = ["Polyline"]

        param1 = arcpy.Parameter(
            displayName='GeMS Fields',
            name='gems_fields',
            datatype='GPValueTable',
            parameterType='Optional',
            direction='Input')

        param1.parameterDependencies = [param0.name]
        cols = [["String", "SymbolCode"],
                ["String", "Symbol Name"]]
        for att in fillGeMSLine.attributelist: cols.append(["String", att])
        param1.columns = cols
        #param1.filters[1].type = "ValueList"

        params = [geodatabase, param0, param1]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def unique_values(self, layer, field):
        with arcpy.da.SearchCursor(layer, field) as cursor:
            return sorted({row[0] for row in cursor})

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
                validation is performed.  This method is called whenever a parameter
                has been changed."""

        if parameters[1].altered and not parameters[1].hasBeenValidated\
                and parameters[0].altered:
            featurename = os.path.basename(str(parameters[1].value))
            self.getDomains(parameters[0].value, featurename)
            v_list = []
            fld_names = self.unique_values(parameters[1].value, 'Symbol')
                #[f.name for f in arcpy.ListFields(parameters[0].value)]
            for fld in fld_names:
                v_list.append([fld, layerCV[fld],
                               '--', '--', '--', '--', '--', '--', '--', '--'])
                del fld
            parameters[2].value = v_list
            del fld_names
            del v_list

            parameters[2].filters[2].list = concealedCV.values()
            parameters[2].filters[3].list = locationConfidenceCV.values()
            parameters[2].filters[4].list = confidenceCV.values()
            parameters[2].filters[5].list = confidenceCV.values()
            parameters[2].filters[6].list = booleanCV.values()
            parameters[2].filters[7].list = booleanCV.values()
            parameters[2].filters[8].list = dataSourceCV.values()
            parameters[2].filters[9].list = typeCV.values()

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def createFieldCalcFunction(self, param1, param2):
        return "def fillInField(Symbol, Param):\n    if Symbol == '"+param1+"':\n        return '"+param2+"'\n" \
                                                                                                   "    else:\n     " \
                                                                                                   "return Param"

    def getDictKey(self, dictionary, value):
        return list(dictionary.keys())[list(dictionary.values()).index(value)]

    def execute(self, parameters, messages):
        fld_names = [f.name for f in arcpy.ListFields(parameters[1].value)]

        valuelist = parameters[2].value

        for row in valuelist:
            i = 0
            messages.addMessage("Changing values for " + row[1])
            for field in fillGeMSLine.attributelist:
                if field not in fld_names:
                    messages.addMessage("skipping field " + field + ", not in feature layer")
                    i = i + 1
                    continue
                rownum = i + 2 #values start in column 3, index 2
                if (row[rownum] == '--'):
                    messages.addMessage("Skipping " + field + " for this row, value is '--'")
                else:
                    messages.addMessage(field + " = " + row[rownum])
                    fieldfunction = self.createFieldCalcFunction(row[0], self.getDictKey(dictofdicts.get(field),
                                                                                         row[rownum]))
                    code = 'fillInField(!Symbol!, !{}!)'.format(field)
                    arcpy.CalculateField_management(parameters[1].value, field,
                                                    code, 'PYTHON_9.3', fieldfunction)
                i = i+1

        return


class exportLinetoShpGeMS(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Export Line To Shapefile GeMS"
        self.description = "This tool takes a feature class, adds several GeMS fields, and exports to a shapefile."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="Line Feature Classes",
            name="in_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
            multiValue=True)

        param0.filter.list = ["Polyline"]

        param1 = arcpy.Parameter(
            displayName="Output Folder",
            name="out_features",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")

        params = [param0, param1]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        fc_list = parameters[0].values
        path = parameters[1].value

        for fc in fc_list:
            arcpy.FeatureClassToShapefile_conversion([fc], path)
            shapefile_dir = str(path) + "\\" + os.path.basename(str(fc)) + ".shp"
            messages.addMessage("Exporting shapefile to " + shapefile_dir + " and adding fields G_Symbol, G_Display, "
                                                                            "G_PolyBldr, G_Label, "
                                                                            "and G_Notes. Transferring data "
                                                                            "from Symbol to G_Symbol if the field "
                                                                            "exists in the feature "
                                                                            "class.")

            arcpy.AddField_management(shapefile_dir, "G_Symbol", "TEXT", field_length=256)
            arcpy.AddField_management(shapefile_dir, "G_Display", "TEXT", field_length=50)
            arcpy.AddField_management(shapefile_dir, "G_PolyBldr", "TEXT", field_length=50)
            arcpy.AddField_management(shapefile_dir, "G_Label", "TEXT", field_length=50)
            arcpy.AddField_management(shapefile_dir, "G_Notes", "TEXT", field_length=256)

            fld_names = [f.name for f in arcpy.ListFields(fc)]

            if ("Symbol" in fld_names):
                arcpy.CalculateField_management(shapefile_dir, "G_Symbol", "!Symbol!", "PYTHON_9.3")
        return


class exportPointtoShpGeMS(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Export Points To Shapefile GeMS"
        self.description = "This tool takes a feature class, adds several GeMS fields, and exports to a shapefile."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="Point Feature Classes",
            name="in_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
            multiValue=True)

        param0.filter.list = ["Point"]

        param1 = arcpy.Parameter(
            displayName="Output Folder",
            name="out_features",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")

        params = [param0, param1]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        fc_list = parameters[0].values
        path = parameters[1].value

        for fc in fc_list:
            arcpy.FeatureClassToShapefile_conversion([fc], path)
            shapefile_dir = str(path) + "\\" + os.path.basename(str(fc)) + ".shp"
            messages.addMessage("Exporting shapefile to " + shapefile_dir + " and adding fields G_Symbol, G_Display, "
                                                                            "G_MapUnit, G_Azimuth, G_Inclnatn, "
                                                                            "G_Label, and G_Notes. Transferring data "
                                                                            "from Symbol to G_Symbol, Azimuth to "
                                                                            "G_Azimuth, and Inclination to G_Inclnatn"
                                                                            " if these fields exist in the feature "
                                                                            "class.")

            arcpy.AddField_management(shapefile_dir, "G_Symbol", "TEXT", field_length=256)
            arcpy.AddField_management(shapefile_dir, "G_Display", "TEXT", field_length=50)
            arcpy.AddField_management(shapefile_dir, "G_MapUnit", "TEXT", field_length=10)
            arcpy.AddField_management(shapefile_dir, "G_Azimuth", "FLOAT")
            arcpy.AddField_management(shapefile_dir, "G_Inclnatn", "FLOAT")
            arcpy.AddField_management(shapefile_dir, "G_Label", "TEXT", field_length=50)
            arcpy.AddField_management(shapefile_dir, "G_Notes", "TEXT", field_length=256)

            fld_names = [f.name for f in arcpy.ListFields(fc)]

            if ("Symbol" in fld_names):
                arcpy.CalculateField_management(shapefile_dir, "G_Symbol", "!Symbol!", "PYTHON_9.3")
            if ("Azimuth" in fld_names):
                arcpy.CalculateField_management(shapefile_dir, "G_Azimuth", "!Azimuth!", "PYTHON_9.3")
            if ("Inclination" in fld_names):
                arcpy.CalculateField_management(shapefile_dir, "G_Inclnatn", "!Inclination!", "PYTHON_9.3")
        return


class exportPolygontoShpGeMS(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Export Polygon To Shapefile GeMS"
        self.description = "This tool takes a feature class, adds several GeMS fields, and exports to a shapefile."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="Point Feature Classes",
            name="in_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
            multiValue=True)

        param0.filter.list = ["Polygon"]

        param1 = arcpy.Parameter(
            displayName="Output Folder",
            name="out_features",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")

        params = [param0, param1]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        fc_list = parameters[0].values
        path = parameters[1].value

        for fc in fc_list:
            arcpy.FeatureClassToShapefile_conversion([fc], path)
            shapefile_dir = str(path) + "\\" + os.path.basename(str(fc)) + ".shp"
            messages.addMessage("Exporting shapefile to " + shapefile_dir + " and adding fields G_MapUnit, G_Label, "
                                                                            "and G_Notes")

            arcpy.AddField_management(shapefile_dir, "G_MapUnit", "TEXT", field_length=10)
            arcpy.AddField_management(shapefile_dir, "G_Label", "TEXT", field_length=50)
            arcpy.AddField_management(shapefile_dir, "G_Notes", "TEXT", field_length=256)

        return



class fillGeMSPointsTesting(object):
    attributelist = ['LocationConfidenceMeters',
                     'IdentityConfidence',
                     'OrientationConfidenceDegrees',
                     'DataSourceID',
                     'LocationSourceID',
                     'OrientationSourceID',
                     'Display',
                     'PlotAtScale']

    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Fill GeMS Points Attribute Table - Testing Version"
        self.description = "This tool fills in some GeMS related attributes given the value of Symbol. " \
                           "This tool will only autofill after both the geodatabase and a feature class are filled " \
                           "in. Note that the tool checks for which of these columns exist in the feature class during " \
                           "the validation phase, so ignore those attributes if not needed.\n If you " \
                           "don't want to edit certain Symbols, use the X next to the value table to delete those rows."
        self.canRunInBackground = False

    def getDomain(self, domains, domainname):
        return next((domain for domain in domains if domain.name == domainname), None).codedValues

    def getDomains(self, gdb, lyrname):
        global layerCV
        global confidenceCV
        global booleanCV
        global dataSourceCV
        global dictofdicts
        global locationConfidenceCV
        global scaleCV

        domains = arcpy.da.ListDomains(gdb)

        layerCV = self.getDomain(domains, lyrname)
        confidenceCV = self.getDomain(domains, "Confidence")
        booleanCV = self.getDomain(domains, "Boolean")
        dataSourceCV = self.getDomain(domains, "DataSource")
        locationConfidenceCV = {'5': '5',
                                '10': '10'}
        scaleCV = {'2400':'2400',
                   '62500':'62500',
                   '50000':'50000',
                   '100000':'100000'}
        dictofdicts = {'LocationConfidenceMeters': locationConfidenceCV,
                       'IdentityConfidence': confidenceCV,
                       'OrientationConfidenceDegrees': locationConfidenceCV,
                       'DataSourceID': dataSourceCV,
                       'LocationSourceID': dataSourceCV,
                       'OrientationSourceID': dataSourceCV,
                       'Display': booleanCV,
                       'PlotAtScale': scaleCV,
                       }

    def getParameterInfo(self):
        geodatabase = arcpy.Parameter(
            displayName="Geodatabase",
            name="gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")

        param0 = arcpy.Parameter(
            displayName='Point Feature Class',
            name='in_features',
            datatype="GPFeatureLayer",
            parameterType='Required',
            direction='Input')

        param0.filter.list = ["Point"]

        param1 = arcpy.Parameter(
            displayName='GeMS Fields',
            name='gems_fields',
            datatype='GPValueTable',
            parameterType='Optional',
            direction='Input')

        param1.parameterDependencies = [param0.name]
        param1.columns = [["String", "Symbol Code"],
                          ["String", "Symbol Name"],
                          ["String", "LocationConfidenceMeters"],
                          ["String", "IdentityConfidence"],
                          ["String", "OrientationConfidenceDegrees"],
                          ["String", "DataSourceID"],
                          ["String", "LocationSourceID"],
                          ["String", "OrientationSourceID"],
                          ["String", "Display"],
                          ["String", "PlotAtScale"],
                          ]
        # param1.filters[1].typ

        #param1.filters[1].type = "ValueList"577

        params = [geodatabase, param0, param1]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def unique_values(self, layer, field):
        with arcpy.da.SearchCursor(layer, field) as cursor:
            return sorted({row[0] for row in cursor})

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
                validation is performed.  This method is called whenever a parameter
                has been changed."""

        if parameters[1].altered and not parameters[1].hasBeenValidated\
                and parameters[0].altered:
            featurename = os.path.basename(str(parameters[1].value))
            self.getDomains(parameters[0].value, featurename)
            v_list = []
            symbol_values = self.unique_values(parameters[1].value, 'Symbol')
                #[f.name for f in arcpy.ListFields(parameters[0].value)]
            for symbol in symbol_values:
                v_list.append([symbol, layerCV[symbol], '5',
                               confidenceCV.values()[1], locationConfidenceCV.values()[1],
                               dataSourceCV.values()[0], dataSourceCV.values()[0],
                               dataSourceCV.values()[0], booleanCV.values()[1],
                               '24000'])
                del symbol
            parameters[2].value = v_list
            del symbol_values
            del v_list
            #parameters[2].filters[2].type = "Field"
            parameters[2].filters[3].list = confidenceCV.values()
            #parameters[2].filters[4].type = "Field"
            parameters[2].filters[5].list = dataSourceCV.values()
            parameters[2].filters[6].list = dataSourceCV.values()
            parameters[2].filters[7].list = dataSourceCV.values()
            parameters[2].filters[8].list = booleanCV.values()
            #parameters[2].filters[9].type = "Field"


        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def createFieldCalcFunction(self, param1, param2):
        return "def fillInField(Symbol, Param):\n    if Symbol == '"+param1+"':\n        return '"+param2+"'\n" \
                                                                                                   "    else:\n     " \
                                                                                                "return Param"

    def getDictKey(self, dictionary, value):
        return list(dictionary.keys())[list(dictionary.values()).index(value)]

    def execute(self, parameters, messages):
        fld_names = [f.name for f in arcpy.ListFields(parameters[1].value)]

        messages.addMessage(fillGeMSPoints.attributelist)
        messages.addMessage(fld_names)

        valuelist = parameters[2].value

        for row in valuelist:
            i = 0
            messages.addMessage("Changing values for " + row[1])
            for field in fillGeMSPoints.attributelist:
                if field not in fld_names:
                    messages.addMessage("skipping field " + field + ", not in feature layer")
                    i = i + 1
                    continue
                rownum = i + 2 #values start in column 3, index 2
                messages.addMessage(field + " = " + row[rownum])
                messages.addMessage("i= " + i + " and rownum = " + rownum)

                if(field == 'PlotAtScale' or field == 'LocationConfidenceMeters' or field == 'OrientationConfidenceDegrees'):
                    fieldfunction = self.createFieldCalcFunction(row[0],row[rownum])
                else:
                    fieldfunction = self.createFieldCalcFunction(row[0], self.getDictKey(dictofdicts.get(field),
                                                                                         row[rownum]))

                code = 'fillInField(!Symbol!, !{}!)'.format(field)
                arcpy.CalculateField_management(parameters[1].value, field,
                                                code, 'PYTHON_9.3', fieldfunction)
                i = i + 1

        return



class fillGeMSPointsTesting2(object):
    attributelist = ['LocationConfidenceMeters',
                     'IdentityConfidence',
                     'OrientationConfidenceDegrees',
                     'DataSourceID',
                     'LocationSourceID',
                     'OrientationSourceID',
                     'Display',
                     'PlotAtScale',
                     'Type']

    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Fill GeMS Points Attribute Table - Testing V2"
        self.description = "This tool fills in some GeMS related attributes given the value of Symbol. " \
                           "This tool will only autofill after both the geodatabase and a feature class are filled " \
                           "in. Note that the tool checks for which of these columns exist in the feature class during " \
                           "the validation phase, so ignore those attributes if not needed.\n If you " \
                           "don't want to edit certain Symbols, use the X next to the value table to delete those rows."
        self.canRunInBackground = False

    def getDomain(self, domains, domainname):
        return self.addBlankToDomain(next((domain for domain in domains if domain.name == domainname),
                                          None).codedValues)

    def addBlankToDomain(self, domain):
        domain['--'] = '--'
        return domain

    def getDomains(self, gdb, lyrname):
        global layerCV
        global confidenceCV
        global booleanCV
        global dataSourceCV
        global dictofdicts
        global locationConfidenceCV
        global scaleCV
        global typeCV

        domains = arcpy.da.ListDomains(gdb)

        layerCV = self.getDomain(domains, lyrname)
        confidenceCV = self.getDomain(domains, "Confidence")
        booleanCV = self.getDomain(domains, "Boolean")
        dataSourceCV = self.getDomain(domains, "DataSource")
        locationConfidenceCV = {'--': '--',
                                '5': '5',
                                '10': '10'}
        scaleCV = {'--': '--',
                   '2400':'2400',
                   '62500':'62500',
                   '50000':'50000',
                   '100000':'100000'}
        typeCV = self.getDomain(domains, "Type")
        dictofdicts = {'LocationConfidenceMeters': locationConfidenceCV,
                       'IdentityConfidence': confidenceCV,
                       'OrientationConfidenceDegrees': locationConfidenceCV,
                       'DataSourceID': dataSourceCV,
                       'LocationSourceID': dataSourceCV,
                       'OrientationSourceID': dataSourceCV,
                       'Display': booleanCV,
                       'PlotAtScale': scaleCV,
                       'Type': typeCV
                       }

    def getParameterInfo(self):
        geodatabase = arcpy.Parameter(
            displayName="Geodatabase",
            name="gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")

        param0 = arcpy.Parameter(
            displayName='Point Feature Class',
            name='in_features',
            datatype="GPFeatureLayer",
            parameterType='Required',
            direction='Input')

        param0.filter.list = ["Point"]

        param1 = arcpy.Parameter(
            displayName='GeMS Fields',
            name='gems_fields',
            datatype='GPValueTable',
            parameterType='Optional',
            direction='Input')

        param1.parameterDependencies = [param0.name]
        #param1.columns = [["String", "Symbol Code"],
        #                  ["String", "Symbol Name"],
        #                  ["String", "LocationConfidenceMeters"],
        #                 ["String", "IdentityConfidence"],
        #                 ["String", "OrientationConfidenceDegrees"],
        #                 ["String", "DataSourceID"],
        #                ["String", "LocationSourceID"],
        #                 ["String", "OrientationSourceID"],
        #                 ["String", "Display"],
        #                 ["String", "PlotAtScale"],
        #                 ]
        # param1.filters[1].typ

        #param1.filters[1].type = "ValueList"
        cols = [["String", "SymbolCode"],
                ["String", "Symbol Name"]]
        for att in fillGeMSPoints.attributelist: cols.append(["String", att])
        param1.columns = cols

        params = [geodatabase, param0, param1]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def unique_values(self, layer, field):
        with arcpy.da.SearchCursor(layer, field) as cursor:
            return sorted({row[0] for row in cursor})

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
                validation is performed.  This method is called whenever a parameter
                has been changed."""

        if parameters[1].altered and not parameters[1].hasBeenValidated\
                and parameters[0].altered:
            featurename = os.path.basename(str(parameters[1].value))
            self.getDomains(parameters[0].value, featurename)
            v_list = []
            symbol_values = self.unique_values(parameters[1].value, 'Symbol')
                #[f.name for f in arcpy.ListFields(parameters[0].value)]
            for symbol in symbol_values:
                v_list.append([symbol, layerCV[symbol],
                               '--', '--', '--', '--', '--', '--', '--', '--', '--'])
                del symbol
            parameters[2].value = v_list
            del symbol_values
            del v_list
            parameters[2].filters[2].list = locationConfidenceCV.values()
            parameters[2].filters[3].list = confidenceCV.values()
            #parameters[2].filters[4].list = locationConfidenceCV.values()
            parameters[2].filters[5].list = dataSourceCV.values()
            parameters[2].filters[6].list = dataSourceCV.values()
            parameters[2].filters[7].list = dataSourceCV.values()
            parameters[2].filters[8].list = booleanCV.values()
            parameters[2].filters[9].list = scaleCV.values()
            parameters[2].filters[10].list = typeCV.values()

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def createFieldCalcFunction(self, param1, param2):
        return "def fillInField(Symbol, Param):\n    if Symbol == '"+param1+"':\n        return '"+param2+"'\n" \
                                                                                                   "    else:\n     " \
                                                                                                "return Param"

    def getDictKey(self, dictionary, value):
        return list(dictionary.keys())[list(dictionary.values()).index(value)]

    def execute(self, parameters, messages):
        fld_names = [f.name for f in arcpy.ListFields(parameters[1].value)]

        messages.addMessage(fillGeMSPoints.attributelist)
        messages.addMessage(fld_names)

        valuelist = parameters[2].value

        for row in valuelist:
            i = 0
            messages.addMessage("Changing values for " + row[1])
            for field in fillGeMSPoints.attributelist:
                if field not in fld_names:
                    messages.addMessage("skipping field " + field + ", not in feature layer")
                    i = i + 1
                    continue
                rownum = i + 2 #values start in column 3, index 2
                messages.addMessage(field + " = " + row[rownum])
                if (row[rownum] == '--'):
                    messages.addMessage("Skipping " + field + " for this row, value is '--'")
                else:
                    messages.addMessage(field + " = " + row[rownum])
                    fieldfunction = self.createFieldCalcFunction(row[0], self.getDictKey(dictofdicts.get(field),
                                                                                         row[rownum]))
                    code = 'fillInField(!Symbol!, !{}!)'.format(field)
                    arcpy.CalculateField_management(parameters[1].value, field,
                                                    code, 'PYTHON_9.3', fieldfunction)
                i = i + 1
        return