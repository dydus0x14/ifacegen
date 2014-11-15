# Created by Evgeny Kamyshanov on November, 2014
# Copyright (c) 2013-2014 BEFREE Ltd. 

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
			return "Int";
		if t == "int64":
			return "Int";
		if t == "double":
			return "Double";
		if t == "raw":
			return "NSDictionary";
		if t == "rawstr":
			return "NSDictionary";
	if isinstance( genType, GenComplexType ):
		return genType.name
	if isinstance( genType, GenListType ):
		return 'NSArray';
	return "_ERROR_"

##############

def writeSwiftTypeSuperInit( fileOut, superType ):
	fileOut.write('super.init(')
	prefx = ""
	for fieldName in superType.allFieldNames():
		fieldType = superType.fieldType( fieldName )
		fieldAlias = superType.fieldAlias( fieldName )
		fileOut.write( prefx + capitalizeFirstLetter( fieldAlias ) + ': ' + fieldAlias )
		prefix = ", "
	fileOut.write(')')	

def writeSwiftTypeInit( fileOut, genType ):
	fileOut.write('\ninit?(')
	prefix = ""
	for fieldName in genType.allFieldNames():
		fieldType = genType.fieldType(fieldName)
		fieldAlias = genType.fieldAlias(fieldName)
#		fileOut.write( prefx + capitalizeFirstLetter(fieldAlias) + ':(' + assumeSwiftType(fieldType) + optionalValue + ')' + fieldAlias )
		fileOut.write(prefix + fieldAlias + ": " + assumeSwiftType(fieldType) + optionalValue )
		prefix = ", "
	fileOut.write(")\n")

def writeSwiftTypeInitDict( fileOut ):
	fileOut.write('\ninit?(dictionary: NSDictionary?, inout error: NSError?)')

def writeSwiftTypeInitData( fileOut ):
	fileOut.write('\ninit?(jsonData: NSData?, inout error: NSError?)')

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
			fileOut.write("var " + genType.fieldAlias( fieldName ) + ": " + assumeSwiftType( fieldType ) + optionalValue + '/*' + assumeSwiftType( fieldType.itemType ) + '*/' + "\n")
		else:
			fileOut.write("var " + genType.fieldAlias( fieldName ) + ": " + assumeSwiftType( fieldType ) + optionalValue + "\n")
		

	if writeDump:
		fileOut.write("\nfunc dumpWithError(inout error: NSError?) -> NSData? {\n")
		fileOut.write("\t var outDict = ")
		unwindInputTypeToSwift( fileOut, genType, 'self', 2 )
		fileOut.write("\n")
		fileOut.write("\treturn NSJSONSerialization.dataWithJSONObject(outDict, options:jsonFormatOption, error:&error)\n}\n")
	if writeConstructors:
		fileOut.write("\n")
		writeSwiftTypeInit( fileOut, genType)
		fileOut.write('{\n')
		if genType.baseType is not None:
			fileOut.write('\t')
			writeSwiftTypeSuperInit( fileOut, genType.baseType )
			fileOut.write('\n')
		else:
			fileOut.write('\tsuper.init()\n')
		
		for fieldName in genType.fieldNames():
			field = genType.fieldType(fieldName)
			fieldAlias = genType.fieldAlias(fieldName)
			fileOut.write('\t\t' + self + fieldAlias + ' = ' + fieldAlias + '\n' )
		fileOut.write('\t}\n')

		fileOut.write('\nfunc readDictionary(dict: NSDictionary) {\n')
		fileOut.write('\tvar tmp: AnyObject?\n\t var error:NSError?\n')
		unwindReturnedTypeToSwift( fileOut, 'dict', genType, 'self', level=1, tmpVarName='tmp' )
		fileOut.write('}\n')

		writeSwiftTypeInitDict( fileOut )
		fileOut.write('{\n')
		fileOut.write('\tsuper.init()\n')
		fileOut.write('\tif ( dictionary == nil ) { return nil }\n')	
		fileOut.write('\t\tself.readDictionary(dictionary)\n')

		writeSwiftTypeInitData( fileOut )
		fileOut.write('{\n')
		fileOut.write('\tsuper.init()\n')
		fileOut.write('\tif ( jsonData == nil ) { return nil }\n')		
		fileOut.write('\t\tvar dict: NSDictionary? = NSJSONSerialization.JSONObjectWithData(jsonData, options:NSJSONReadingAllowFragments, error:&error)\n');
		fileOut.write('\t\tif ( &error != nil ) {\n\t\t\treturn nil\n\t\t}\n')		
		fileOut.write('\t\tself.readDictionary(dict)\n')
		fileOut.write('\t}\n')
	fileOut.write("}\n")

def writeSwiftMethod( fileOut, method ):
	argDecoration = " "
	if len(method.prerequestTypes) + len(method.requestTypes) > 1:
		argDecoration = ",\n\t\t"

	fileOut.write( "func " + method.name )

	pref = "With("

	prerequestFormalType = method.formalPrerequestType();
	requestFormalType = method.formalRequestType();

#set name and parameters for method 
	if prerequestFormalType is not None:
		for argName in prerequestFormalType.fieldNames():
			argType = prerequestFormalType.fieldType(argName)
			argAlias = prerequestFormalType.fieldAlias(argName)
			typeStr = assumeSwiftType( argType )
			fileOut.write( pref + capitalizeFirstLetter( argAlias ) + " " + argAlias + ":" + typeStr + optionalValue )
			pref = argDecoration + "and"

	if len(method.requestTypes) != 0:
		for argName in requestFormalType.fieldNames():
			argType = requestFormalType.fieldType(argName)
			argAlias = requestFormalType.fieldAlias(argName)
			typeStr = assumeSwiftType( argType )
			fileOut.write( pref + capitalizeFirstLetter( argAlias ) + " " + argAlias + ":" + typeStr + optionalValue  )
			pref = argDecoration + "and"

	fileOut.write( pref + "Error, inout error: NSError" + optionalValue)

	if method.responseType is not None:
		if isinstance( method.responseType, GenListType ):
			fileOut.write( ")" + " -> (" + assumeSwiftType( method.responseType ) + optionalValue + '/*' + assumeSwiftType( method.responseType.itemType ) + '*/' + ")" )
		else:
			fileOut.write( ")" + " -> (" + assumeSwiftType( method.responseType ) + optionalValue + ")" )
	else:	
			fileOut.write( ")" )
	
	fileOut.write(" {\n")
#implement method
	tmpVarName = "tmp"
	fileOut.write('\tvar ' + tmpVarName + ": AnyObject?\n")

	prerequestFormalType = method.formalPrerequestType();
	requestFormalType = method.formalRequestType();

	pref = "\t\t"
	if prerequestFormalType is not None:
		fileOut.write('\ttransport.setRequestParams([\n')
		for argName in prerequestFormalType.fieldNames():
			arg = prerequestFormalType.fieldType(argName)
			argAlias = prerequestFormalType.fieldAlias(argName)
			fileOut.write(argName + " : " + decorateSwiftInputType( argAlias, arg ) )
			pref = ',\n\t\t'
		fileOut.write('\n\t])\n')

	if requestFormalType is not None:		
		fileOut.write("\tvar inputDict: NSDictionary? = ")
		unwindInputTypeToSwift( fileOut, method.formalRequestType(), None, 2 )
		
		fileOut.write("\n")

		fileOut.write("\tvar inputData: NSData? = NSJSONSerialization.dataWithJSONObject(inputDict, options:jsonFormatOption, error:&error)\n")
		fileOut.write('\tif ( !transport.writeAll(inputData, prefix:"' + method.prefix + '", error:&error) ) {\n')
	else:
		fileOut.write('\tif ( !transport.writeAll(nil, prefix:"' + method.prefix + '", error:&error) ) {\n')

	# fileOut.write('\t\tNSLog(@"' + method.name + ': server call failed, %@", *error);\n')

	if method.responseType is None:
		fileOut.write('\t\treturn\n\t}\n')		
		fileOut.write('}\n')
		return
	else:
		fileOut.write('\t\treturn nil\n\t}\n')

	fileOut.write('\tvar outputData: NSData? = transport.readAll()\n\tif ( outputData == nil ) {\n')
	# fileOut.write('\t\tNSLog(@"' + method.name + ': empty answer");\n\t\treturn nil;\n\t}\n')
	fileOut.write('\t\treturn nil\n\t}\n')

	outputName = 'output'

	outputStatement = "var " + outputName + ': NSDictionary?'
	if isinstance( method.responseType, GenListType ):
		outputStatement = "var " + outputName + ": NSArray?"

	fileOut.write('\t' + outputStatement + ' = NSJSONSerialization.JSONObjectWithData(outputData, options:NSJSONReadingAllowFragments, error:&error)\n');
	fileOut.write('\tif ( &error != nil ) {\n\t\treturn nil\n\t}\n')

	retVal = unwindReturnedTypeToSwift( fileOut, outputName, method.responseType, method.responseArgName, 1, tmpVarName )

	fileOut.write('\treturn ' + retVal + '\n')	
	fileOut.write("}\n\n")
# TODO: implement it

def decorateSwiftReturnedType( levelTmpVar, objcRetTypeStr, retType ):
# TODO: check it	
	formatNSNumberStr = '( {0} = {1}, {0}.isEqual(NSNull.null)) ? {2} : (({3}){0}).{4} )'
	formatNSStringStr = '( {0} = {1}, {0}.isEqual(NSNull.null)) ? nil : {0} as String )'
	formatNSDictionaryStr = '( {0} = {1}, {0}.isEqual(NSNull.null)) ? nil : {0} as NSDictionary )'
	formatRawNSDictionaryStr = '( {0} = {1}, {0}.isEqual(NSNull.null) ? nil : (NSJSONSerialization JSONObjectWithData:(({0} as String).dataUsingEncoding:NSUTF8StringEncoding(), options:NSJSONReadingAllowFragments, error:&error) )'		
	if retType.sType == "bool":
		return formatNSNumberStr.format( levelTmpVar, objcRetTypeStr, 'false', 'NSNumber', 'boolValue' )
	if retType.sType == "int32":
		return formatNSNumberStr.format( levelTmpVar, objcRetTypeStr, '0', 'NSNumber', 'intValue' )
	if retType.sType == "int64":
		return formatNSNumberStr.format( levelTmpVar, objcRetTypeStr, '0L', 'NSNumber', 'longLongValue' )
	if retType.sType == "double":
		return formatNSNumberStr.format( levelTmpVar, objcRetTypeStr, '0.0', 'NSNumber', 'doubleValue' )
	if retType.sType == "string":
		return formatNSStringStr.format( levelTmpVar, objcRetTypeStr )
	if retType.sType == "raw":
		return formatNSDictionaryStr.format( levelTmpVar, objcRetTypeStr )
	if retType.sType == "rawstr":
		return formatRawNSDictionaryStr.format( levelTmpVar, objcRetTypeStr )
	return "ERROR";

def unwindReturnedTypeToSwift( fileOut, objcDictName, outType, outArgName, level, tmpVarName ):
# TODO: check it
	if isinstance( outType, GenIntegralType ): 	
		if outArgName is None:
			#return ( decorateOBJCReturnedType( tmpVarName, objcDictName, outType ) ) #TODO: fix this strange 'objcDictName' behavior in case of lists unwind
			return objcDictName;
		else:
			return ( decorateSwiftReturnedType( tmpVarName, objcDictName + '.objectForKey("' + outArgName + '")', outType ) )

	if isinstance( outType, GenComplexType ):
		objCResType = assumeSwiftType( outType )
		currentDictName = objcDictName
		resName = outType.name + str( newVariableCounter() )	

		if outArgName is None or outArgName != 'self':
			fileOut.write('\t'*level + objCResType + optionalValue + ' ' + resName + '\n')
		else:		
			resName = 'self'

		if outArgName is not None and outArgName != 'self':
			currentDictName = objcDictName + capitalizeFirstLetter( outArgName ) + str( newVariableCounter() )
			fileOut.write('\t'*level + "var " + currentDictName + ': NSDictionary? = ' + objcDictName + '.objectForKey("' + outArgName + '")\n')
			fileOut.write('\t'*level + 'if ( ' + currentDictName + ' != nil && !' + currentDictName + '.isEqual(NSNull.null)) {\n')
			level += 1
 			fileOut.write( '\t'*level + resName + ' = ' + objCResType + '()\n' )
 		elif outArgName != 'self':
 			fileOut.write( '\t'*level + resName + ' = ' + objCResType + '()\n' )

#TODO: uncomment after optional arguments appear
#			errMsg = '@"Can`t parse answer from server in ' + outArgName + '"'
#			fileOut.write('\tif ( ' + currentDictName + ' != nil ) {\n\t\tNSLog(' + errMsg +  ');\n')
#			fileOut.write('\t\t*error = [self errorWithMessage:' + errMsg + '];\n')
#			fileOut.write('\t\treturn nil;\n\t}\n')

		for fieldKey in outType.allFieldNames():
			outField = outType.fieldType(fieldKey)
			value = unwindReturnedTypeToSwift( fileOut, currentDictName, outField, fieldKey, level+1, tmpVarName )
			fileOut.write('\t'*level + resName + '.' + outType.fieldAlias(fieldKey) + ' = ' + value + '\n')

		if outArgName is not None and outArgName != 'self':
			level -= 1
			fileOut.write('\t'*level + '}\n')

		return resName

	if isinstance( outType, GenListType ):
		if outArgName is None:
			currentArrayName = objcDictName
		else:
			currentArrayName = objcDictName + capitalizeFirstLetter( outArgName ) + str( newVariableCounter() )
			fileOut.write('\t'*level + "var " + currentArrayName  + ': NSArray? ' + ' = ' + objcDictName + '.objectForKey("' + outArgName + '")\n')

		objCResType = assumeSwiftType( outType )
		if outArgName is not None:
			resName = outArgName + str(level)
		else:
			resName = "array" + str(level)

		fileOut.write('\t'*level + "var " + resName + ': NSMutableArray?'  + '\n')

		fileOut.write('\t'*level + 'if ( ' + currentArrayName + ' != nil && !' + currentArrayName + '.isEqual(NSNull.null)) {\n')
		level += 1

		fileOut.write('\t'*level + resName + ' = NSMutableArray(capacity: ' + currentArrayName + '.count)\n')

		fileOut.write('\t'*level + 'for ( item in ' + currentArrayName + ') {\n' )
		item = unwindReturnedTypeToSwift( fileOut, 'item', outType.itemType, None, level+1, tmpVarName )
		fileOut.write( '\t'*(level+1) + resName + '.addObject(' + item + ')\n' )
		fileOut.write('\t'*level + '}\n' )

		level -= 1
		fileOut.write('\t'*level + '}\n')

		return resName

def decorateSwiftInputType( objcInpTypeStr, inpType ):
	prefix = "NULLABLE("
	suffix = ")"
	if inpType.sType == 'bool':
		prefix = 'NSNumber(bool: '
		suffix = ")"
	if inpType.sType == 'int32':
		prefix = 'NSNumber(int: '
		suffix = ')'
	if inpType.sType == 'int64':
		prefix = 'NSNumber(longLong: '
		suffix = ')'
	if inpType.sType == 'double':
		prefix = 'NSNumber(double: '
		suffix = ')'
	if inpType.sType == 'rawstr':
		prefix = 'NSString(data:NSJSONSerialization.dataWithJSONObject('
		suffix =  ', options:jsonFormatOption, error:&error), encoding:NSUTF8StringEncoding)'
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
				objcStatement = inputType.fieldAlias(argName)
				if inputArgName is not None:
					objcStatement = inputArgName + '.' + inputType.fieldAlias(argName)
				unwindInputTypeToSwift( fileOut, fieldType, objcStatement, level+1 )

			fileOut.write("\n" + '\t'*level + "]")

		elif isinstance( inputType, GenListType ):
			if isinstance( inputType.itemType, GenIntegralType ):
				fileOut.write( 'NULLABLE(' + inputArgName + ')' )
			else:
				fileOut.write('{ (inArr: NSArray?) -> (NSArray?) in \n' + '\t'*level + 'var resArr: NSMutableArray?  = NSMutableArray(capacity: inArr.count))\n')
				fileOut.write('\t'*level + 'for ' + ' inObj: ' + assumeSwiftType(inputType.itemType) + ' in inArr {\n' ) 
				fileOut.write('\t'*level + '\tresArr.addObject(')
				unwindInputTypeToSwift( fileOut, inputType.itemType, 'inObj', level+2 )
				fileOut.write( ')\n' + '\t'*level + '\t}\n' + '\t'*level + 'return resArr } ( ' + inputArgName + ' )' )

def writeWarning( fileOut, inputName ):
	fileOut.write("/**\n")
	fileOut.write(" * @generated\n *\n")
	fileOut.write(" * AUTOGENERATED. DO NOT EDIT.\n *\n")
	fileOut.write(" */\n\n")

def writeSwiftIface( fileOut, inputName ):
	fileOut.write("\nclass " + inputName + " {")
	fileOut.write("\nvar transport: IFTransport\n")
	fileOut.write("\ninit(transport: IFTransport) {\n")
	fileOut.write("\tsuper.init()\n\tself.transport = transport\n}\n")
	fileOut.write('\nfunc errorWithMessage(msg: NSString?) -> NSError? {\n')
	fileOut.write('\tvar errData: NSDictionary? = NSDictionary(object: msg, forKey: NSLocalizedDescriptionKey)\n')
	fileOut.write('\treturn NSError(domain: NSStringFromClass(self.class), code:0, userInfo:errData);\n}\n')	
	

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
	parser.add_argument('--prefix', action='store', required=False, help='Class and methods prefix')
	parser.add_argument('-o', '--outdir', action='store', default="gen-swift", required=False, help="Output directory name")

	parsedArgs = parser.parse_args()
	if len(sys.argv) == 1:
	    parser.print_help()
	    return 0

	try:
		for rpcInput in parsedArgs.rpcInput:
			processJSONIface( rpcInput, parsedArgs.prefix, parsedArgs.outdir )
	except Exception as ex:
		print( str(ex) )
		sys.exit(1)

	return 0

#########

if __name__ == "__main__":
	main()




















