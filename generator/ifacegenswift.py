# Created by Anton Davydov on November, 2014
# Copyright (c) 2013-2014. 

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from ifaceparser import *
import argparse
import sys
import types
import os
from collections import OrderedDict

variableCounter = 0
optionalValue = '?'
self = 'self.'
tab = 0

def newVariableCounter():
	global variableCounter
	oldVariableCounter = variableCounter
	variableCounter += 1
	return oldVariableCounter

def assumeSwiftType( genType ):
	if isinstance( genType, GenIntegralType ):
		t = genType.sType
		if t == "string":
			return "String"
		if t == 'bool':
			return "Bool";
		if t == "int32":
			return "Int32";
		if t == "int64":
			return "Int64";
		if t == "double":
			return "Double";
		if t == "raw":
			return "[String : AnyObject]"; #"NSDictionary";
		if t == "rawstr":
			return "[String : AnyObject]"; #"NSDictionary";
	if isinstance( genType, GenComplexType ):
		return genType.name
	if isinstance( genType, GenListType ):
		return '[' + genType.itemType.name + ']';
	return "_ERROR_"

##############
def writeHeader( fileOut ):
	fileOut.write("import Foundation\n")

def writeSwiftTypeSuperInit( fileOut, superType ):
	fileOut.write('\t\tsuper.init(')
	prefx = ""
	for fieldName in superType.allFieldNames():
		fieldType = superType.fieldType( fieldName )
		fieldAlias = superType.fieldAlias( fieldName )
		fileOut.write( prefx + fieldAlias + ': ' + fieldAlias )
		prefx = ", "
	fileOut.write(')')	

def writeSwiftDefaultInit( fileOut ):
	fileOut.write('\n\tinit() {}\n')

def writeSwiftTypeInit( fileOut, genType ):
	fileOut.write('\tinit?(')
	prefix = ""
	for fieldName in genType.allFieldNames():
		fieldType = genType.fieldType(fieldName)
		fieldAlias = genType.fieldAlias(fieldName)
		fileOut.write(prefix + fieldAlias + ": " + assumeSwiftType(fieldType) + optionalValue )
		prefix = ", "
	fileOut.write(")\n")

def writeSwiftTypeInitDict( fileOut ):
	fileOut.write('\n\tinit?(dictionary: [String : AnyObject]!, inout error: NSError?)')

def writeSwiftTypeInitData( fileOut ):
	fileOut.write('\n\tinit?(jsonData: NSData!, inout error: NSError?)')

def writeSwiftType( fileOut, genType, writeConstructors, writeDump ):
	if isinstance( genType, GenIntegralType ) or isinstance( genType, GenListType ):
		return
	if genType.baseType is not None:
		fileOut.write("\nclass " + genType.name + ": " + genType.baseType.name + " {" + "\n")
	else:
		fileOut.write("\nclass " + genType.name + " {" + "\n")

	for fieldName in genType.fieldNames():
		fieldType = genType.fieldType(fieldName)
		if isinstance( fieldType, GenListType ):
			fileOut.write("\tvar " + genType.fieldAlias( fieldName ) + ": [" + assumeSwiftType( fieldType.itemType ) + ']' + optionalValue + "\n")
		else:
			fileOut.write("\tvar " + genType.fieldAlias( fieldName ) + ": " + assumeSwiftType( fieldType ) + optionalValue + "\n")
	if writeDump:
		fileOut.write("\tprivate let checkNil = { (obj: AnyObject!)->(AnyObject) in return  obj == nil ? NSNull() : obj }\n")

	writeSwiftDefaultInit( fileOut )
	if writeConstructors:
		fileOut.write("\n")
		writeSwiftTypeInit( fileOut, genType)
		fileOut.write('\t{\n')
		if genType.baseType is not None:
			fileOut.write('\t')
			writeSwiftTypeSuperInit( fileOut, genType.baseType )
			fileOut.write('\n')
		#else:
			#fileOut.write('\tsuper.init()\n')
		
		for fieldName in genType.fieldNames():
			field = genType.fieldType(fieldName)
			fieldAlias = genType.fieldAlias(fieldName)
			fileOut.write('\t\t' + self + fieldAlias + ' = ' + fieldAlias + '\n' )
		fileOut.write('\t}\n')

		fileOut.write('\n\tfunc readDictionary(dict: [String : AnyObject]) {\n')
		#fileOut.write('\tvar tmp: AnyObject?\n\t var error:NSError?\n')
		unwindReturnedTypeToSwift( fileOut, 'dict', genType, 'self', level=2, tmpVarName='tmp' )
		fileOut.write('\t}\n')

		writeSwiftTypeInitDict( fileOut )
		fileOut.write('{\n')
		#fileOut.write('\tsuper.init()\n')
		fileOut.write('\t\tif ( dictionary == nil ) { return nil }\n')	
		fileOut.write('\t\tself.readDictionary(dictionary)\n')
		fileOut.write('\t}\n')

		writeSwiftTypeInitData( fileOut )
		fileOut.write('{\n')
		#fileOut.write('\tsuper.init()\n')
		fileOut.write('\t\tif ( jsonData == nil ) { return nil }\n')		
		fileOut.write('\t\tvar dict = NSJSONSerialization.JSONObjectWithData(jsonData, options:.AllowFragments, error:&error) as? [String : AnyObject]\n');
		fileOut.write('\t\tif ( error != nil ) {\n\t\t\treturn nil\n\t\t}\n')		
		fileOut.write('\t\tself.readDictionary(dict!)\n')
		fileOut.write('\t}\n')
	if writeDump:
		fileOut.write("\n\tfunc dump(inout error: NSError?) -> NSData? {\n")
		fileOut.write("\t\tvar outDict: [String : AnyObject] = ")
		unwindInputTypeToSwift( fileOut, genType, 'self', 3 )
		fileOut.write("\n")
		fileOut.write("\t\treturn NSJSONSerialization.dataWithJSONObject(outDict, options: .PrettyPrinted, error:&error)\n\t}\n")
	fileOut.write("}\n")

def writeSwiftMethod( fileOut, method ):
	argDecoration = " "
	if len(method.prerequestTypes) + len(method.requestTypes) > 1:
		argDecoration = ",\n\t\t"

	fileOut.write( "\tfunc " + method.name + "(")
	pref = ""
	prerequestFormalType = method.formalPrerequestType();
	requestFormalType = method.formalRequestType();

#set name and parameters for method 
	if prerequestFormalType is not None:
		for argName in prerequestFormalType.fieldNames():
			argType = prerequestFormalType.fieldType(argName)
			argAlias = prerequestFormalType.fieldAlias(argName)
			typeStr = assumeSwiftType( argType )
			fileOut.write( pref + argAlias + ":" + typeStr + optionalValue )
			pref = ", "

	if len(method.requestTypes) != 0:
		for argName in requestFormalType.fieldNames():
			argType = requestFormalType.fieldType(argName)
			argAlias = requestFormalType.fieldAlias(argName)
			typeStr = assumeSwiftType( argType )
			fileOut.write( pref + argAlias + ":" + typeStr + optionalValue )

	fileOut.write( pref + " inout error: NSError?")

	if method.responseType is not None:
		if isinstance( method.responseType, GenListType ):
			fileOut.write( ")" + " -> (" + assumeSwiftType( method.responseType.itemType ) + optionalValue + ")" )
		else:
			fileOut.write( ")" + " -> (" + assumeSwiftType( method.responseType ) + optionalValue + ")" )
	else:	
			fileOut.write( ")" )
	
	fileOut.write(" {\n")
#implement method
	tmpVarName = "tmp"
	fileOut.write('\tvar ' + tmpVarName + ": AnyObject?\n")
	fileOut.write('\tvar er: NSError?\n')

	prerequestFormalType = method.formalPrerequestType();
	requestFormalType = method.formalRequestType();

	pref = "\t\t"
	if prerequestFormalType is not None:
		fileOut.write('\ttransport.setRequestParams([\n')
		for argName in prerequestFormalType.fieldNames():
			arg = prerequestFormalType.fieldType(argName)
			argAlias = prerequestFormalType.fieldAlias(argName)
			fileOut.write(pref + '"' + argName + '" : ' + "{$0 == nil ? NSNull() : $0}(" + decorateSwiftInputType( argAlias, arg ) + ")")
			pref = ',\n\t\t'
		fileOut.write('\n\t])\n')

	if requestFormalType is not None:		
		fileOut.write("\tvar inputDict: [String : AnyObject]? = ")
		unwindInputTypeToSwift( fileOut, method.formalRequestType(), None, 2 )
		
		fileOut.write("\n")

		fileOut.write("\tvar inputData: NSData? = NSJSONSerialization.dataWithJSONObject(inputDict, options:0, error:&error)\n")
		fileOut.write('\tif transport.writeAll(inputData, prefix:"' + method.prefix + '", error:&er) == false {\n')
	else:
		fileOut.write('\tif transport.writeAll(nil, prefix:"' + method.prefix + '", error:&er) == false {\n')

	# fileOut.write('\t\tNSLog(@"' + method.name + ': server call failed, %@", *error);\n')

	if method.responseType is None:
		fileOut.write('\t\terror = er\n')
		fileOut.write('\t\treturn\n\t}\n')		
		fileOut.write('}\n')
		return
	else:
		fileOut.write('\t\terror = er\n')
		fileOut.write('\t\treturn nil\n\t}\n')

	fileOut.write('\tvar outputData: NSData! = transport.readAll()\n\tif ( outputData == nil ) {\n')
	# fileOut.write('\t\tNSLog(@"' + method.name + ': empty answer");\n\t\treturn nil;\n\t}\n')
	fileOut.write('\t\treturn nil\n\t}\n')

	outputName = 'output'

	outputStatement ='[String : AnyObject]'
	if isinstance( method.responseType, GenListType ):
		outputStatement ='[' + assumeSwiftType (method.responseType ) +']'

	fileOut.write('\t' +  "var " + outputName + ': ' + outputStatement + '! = NSJSONSerialization.JSONObjectWithData(outputData, options: .AllowFragments, error:&er) as? ' +  outputStatement + '\n');
	fileOut.write('\tif ( error != nil ) {\n\t\terror = er\n\t\treturn nil\n\t}\n')

	retVal = unwindReturnedTypeToSwift( fileOut, outputName, method.responseType, method.responseArgName, 1, tmpVarName )

	fileOut.write('\treturn ' + retVal + '\n')	
	fileOut.write("}\n\n")
# TODO: implement it

def decorateSwiftReturnedType( levelTmpVar, objcRetTypeStr, retType ):
# TODO: check it	
	formatNSNumberStr = "({1} as? {3})?.{4}"#'( {0} = {1}, {0}.isEqual(NSNull()) ? {2} : ({0} as {3}).{4} )'
	formatNSStringStr = '{1} as? String'
	formatNSDictionaryStr = '{1} as? [String : AnyObject]'
	formatRawNSDictionaryStr = ' {0} as? NSNull != nil ? nil : NSJSONSerialization.JSONObjectWithData(({0} as String).dataUsingEncoding(NSUTF8StringEncoding, allowLossyConversion: false)!, options: .AllowFragments, error:nil) as? [String : AnyObject]'		
	if retType.sType == "bool":
		return formatNSNumberStr.format( levelTmpVar, objcRetTypeStr, 'false', 'NSNumber', 'boolValue' )
	if retType.sType == "int32":
		return formatNSNumberStr.format( levelTmpVar, objcRetTypeStr, '0', 'NSNumber', 'intValue' )
	if retType.sType == "int64":
		return formatNSNumberStr.format( levelTmpVar, objcRetTypeStr, '0', 'NSNumber', 'longLongValue' )
	if retType.sType == "double":
		return formatNSNumberStr.format( levelTmpVar, objcRetTypeStr, '0.0', 'NSNumber', 'doubleValue' )
	if retType.sType == "string":
		return formatNSStringStr.format( levelTmpVar, objcRetTypeStr )
	if retType.sType == "raw":
		return formatNSDictionaryStr.format( levelTmpVar, objcRetTypeStr )
	if retType.sType == "rawstr":
		return formatRawNSDictionaryStr.format( objcRetTypeStr )
	return "ERROR";

def unwindReturnedTypeToSwift( fileOut, objcDictName, outType, outArgName, level, tmpVarName ):
# TODO: check it
	if isinstance( outType, GenIntegralType ): 	
		if outArgName is None:
			#return ( decorateOBJCReturnedType( tmpVarName, objcDictName, outType ) ) #TODO: fix this strange 'objcDictName' behavior in case of lists unwind
			return objcDictName;
		else:
			return ( decorateSwiftReturnedType( tmpVarName, objcDictName + '["' + outArgName + '"]', outType ) )

	if isinstance( outType, GenComplexType ):
		objCResType = assumeSwiftType( outType )
		currentDictName = objcDictName
		resName = outType.name + str( newVariableCounter() )	

		optionalValueForAccess = optionalValue
		if outArgName is None or outArgName != 'self':
			if objcDictName == 'item':
				fileOut.write('\t'*level + "var " + resName )# + ": " + objCResType + "?")
			else:
				fileOut.write('\t'*(level-1) + "var " + resName )
		else:		
			resName = 'self'
			optionalValueForAccess = ""

		if outArgName is not None and outArgName != 'self':
 			fileOut.write( ' = ' + objCResType + '()\n' )
			currentDictName = objcDictName + capitalizeFirstLetter( outArgName ) + str( newVariableCounter() )
			fileOut.write('\t'*(level - 1) + 'if let ' + currentDictName + ' = ' + objcDictName + '["' + outArgName + '"] as? [String : AnyObject]  {\n')
 		elif outArgName != 'self':
 			fileOut.write( ' = ' + objCResType + '()\n' )

#TODO: uncomment after optional arguments appear
#			errMsg = '@"Can`t parse answer from server in ' + outArgName + '"'
#			fileOut.write('\tif ( ' + currentDictName + ' != nil ) {\n\t\tNSLog(' + errMsg +  ');\n')
#			fileOut.write('\t\t*error = [self errorWithMessage:' + errMsg + '];\n')
#			fileOut.write('\t\treturn nil;\n\t}\n')

		for fieldKey in outType.allFieldNames():
			outField = outType.fieldType(fieldKey)
			value = unwindReturnedTypeToSwift( fileOut, currentDictName, outField, fieldKey, level+1, tmpVarName )
			fileOut.write('\t'*level + resName +'.' + outType.fieldAlias(fieldKey) + ' = ' + value + '\n')

		if outArgName is not None and outArgName != 'self':
			level -= 1
			fileOut.write('\t'*level + '}\n')

		return resName

	if isinstance( outType, GenListType ):
		level -= 1
		if outArgName is None:
			currentArrayName = objcDictName
		else:
			currentArrayName = objcDictName + capitalizeFirstLetter( outArgName ) + str( newVariableCounter() )
			fileOut.write('\t'*level + "let " + currentArrayName + ': [Dictionary<String, AnyObject>]! = ' + objcDictName + '["' + outArgName + '"] as? [Dictionary<String, AnyObject>]\n')

		objCResType = assumeSwiftType( outType )
		if outArgName is not None:
			resName = outArgName + str(level)
		else:
			resName = "array" + str(level)

		fileOut.write('\t'*level + "var " + resName + ': ' + assumeSwiftType( outType ) + '!\n')
		fileOut.write('\t'*level + 'if ( ' + currentArrayName + ' != nil ) {\n')
		level += 1

		fileOut.write('\t'*level + resName + ' = []\n')
		fileOut.write('\t'*level + 'for item in ' + currentArrayName + ' {\n' )
		item = unwindReturnedTypeToSwift( fileOut, 'item', outType.itemType, None, level+1, tmpVarName )
		fileOut.write( '\t'*(level+1) + resName + '.append(' + item + ')\n' )
		fileOut.write('\t'*level + '}\n' )

		level -= 1
		fileOut.write('\t'*level + '}\n')

		return resName

def decorateSwiftInputType( objcInpTypeStr, inpType ):
	prefix = "self.checkNil("
	suffix = ")"

	if inpType.sType == 'rawstr':
		prefix = objcInpTypeStr + ' == nil ? NSNull() : NSString(data:NSJSONSerialization.dataWithJSONObject(self.checkNil('
		suffix =  ') , options: NSJSONWritingOptions.PrettyPrinted, error:&error)!, encoding: NSUTF8StringEncoding)!'
	if inpType.sType == 'int64':
		prefix = objcInpTypeStr + " == nil ? NSNull() : NSNumber(longLong: "
		suffix = '!)'
	if inpType.sType == 'int32':
		prefix = objcInpTypeStr + " == nil ? NSNull() : NSNumber(int: ("
		suffix = ')!)'
	return prefix + objcInpTypeStr + suffix

def unwindInputTypeToSwift( fileOut, inputType, inputArgName, level  ):
		if isinstance( inputType, GenIntegralType ):
			fileOut.write( decorateSwiftInputType( inputArgName, inputType ) )
	
		elif isinstance( inputType, GenComplexType ):
			fileOut.write( "[\n" )
	
			firstArgument = True
			for argName in inputType.allFieldNames():
				if not firstArgument:
					fileOut.write(",\n")
				firstArgument = False

				fileOut.write( '\t'*level + '"' + argName + '" : ')
				fieldType = inputType.fieldType(argName)
				objcStatement = inputArgName + '.' + inputType.fieldAlias(argName)
				if isinstance( fieldType, GenComplexType ):
					objcStatement = objcStatement + '?'
				unwindInputTypeToSwift( fileOut, fieldType, objcStatement, level+1 )

			fileOut.write("\n" + '\t'*(level-1) + "]")

		elif isinstance( inputType, GenListType ):
			if isinstance( inputType.itemType, GenIntegralType ):
				#fileOut.write( 'self.NULLABLE(' + inputArgName + ')' )
				fileOut.write(inputArgName)
			else:
				fileOut.write('{ (inArr: [' + assumeSwiftType(inputType.itemType) + ']!) -> (AnyObject) in \n' + '\t'*level + 'if inArr == nil { return NSNull() }\n' + '\t'*level + 'var resArr: [Dictionary<String, AnyObject>] = []\n')
				fileOut.write('\t'*level + 'for ' + ' inObj in inArr {\n' ) 
				fileOut.write('\t'*level + '\tresArr.append(')
				unwindInputTypeToSwift( fileOut, inputType.itemType, 'inObj', level+2 )
				fileOut.write( ')\n' + '\t'*level + '}\n' + '\t'*level + 'return resArr } ( ' + inputArgName + ' )' )

def writeWarning( fileOut, inputName ):
	fileOut.write("/**\n")
	fileOut.write(" * @generated\n *\n")
	fileOut.write(" * AUTOGENERATED. DO NOT EDIT.\n *\n")
	fileOut.write(" */\n\n")

def writeSwiftIface( fileOut, inputName ):
	fileOut.write("\nclass " + inputName + " {")
	fileOut.write("\n\tvar transport: IFTransport\n")
	fileOut.write("\n\tinit(transport: IFTransport) {\n")
	#fileOut.write("\tsuper.init()\n\t\n")
	fileOut.write("\t\tself.transport = transport\n\t}\n")
	fileOut.write('\n\tfunc errorWithMessage(msg: NSString!) -> NSError? {\n')
	fileOut.write('\t\tvar errData: NSDictionary? = NSDictionary(object: msg, forKey: NSLocalizedDescriptionKey)\n')
	fileOut.write('\t\treturn NSError(domain: "", code:0, userInfo:errData)\n\t}')
	#here was NSStringFromClass	
	

#####################################

def processJSONIface( jsonFile, typeNamePrefix, outDir ):

	if outDir is not None:
		genDir = os.path.abspath( outDir )

	if typeNamePrefix is not None:
		GenType.namePrefix = typeNamePrefix
		GenMethod.namePrefix = typeNamePrefix

	module = parseModule( jsonFile )
	if module is None:
		print "Can't load module " + jsonFile;
		return

	if not os.path.exists( genDir ):
	    os.makedirs( genDir )

	swiftCIface = open( os.path.join( genDir, module.name + ".swift" ), "wt" )

#writeWarning( swiftIface, None )

#writeObjCImplHeader( objCImpl, module.name )			

	writeHeader( swiftCIface )

	for genTypeKey in module.typeList.keys():
		writeAll = ( genTypeKey in module.structs )							
		writeSwiftType( swiftCIface, module.typeList[genTypeKey], writeDump=writeAll, writeConstructors=writeAll )

	writeSwiftIface( swiftCIface, module.name )
	if len( module.methods ) != 0:
		swiftCIface.write("\n/* methods */\n\n")

	for method in module.methods:
		writeSwiftMethod( swiftCIface, method)
	swiftCIface.write('\n}')

def main():
	parser = argparse.ArgumentParser(description='JSON-Swift interface generator')
	
	parser.add_argument('rpcInput', metavar='I', type=unicode, nargs = '+', help = 'Input JSON RPC files')
	parser.add_argument('-o', '--outdir', action='store', default="gen-swift", required=False, help="Output directory name")

	parsedArgs = parser.parse_args()
	if len(sys.argv) == 1:
	    parser.print_help()
	    return 0

	try:
		for rpcInput in parsedArgs.rpcInput:
			processJSONIface( rpcInput, "", parsedArgs.outdir )
	except Exception as ex:
		print( str(ex) )
		sys.exit(1)

	return 0

#########

if __name__ == "__main__":
	main()




















