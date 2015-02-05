# Created by Evgeny Kamyshanov on March, 2014
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
from string import Template

variableCounter = 0
def newVariableCounter():
	global variableCounter
	oldVariableCounter = variableCounter
	variableCounter += 1
	return oldVariableCounter

def assumeOBJCType( genType ):
	if isinstance( genType, GenIntegralType ):
		t = genType.sType
		if t == "string":
			return "NSString"
		if t == 'bool':
			return "BOOL";
		if t == "int32":
			return "int32_t";
		if t == "int64":
			return "int64_t";
		if t == "double":
			return "double_t";
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

def writeOBJCTypeSuperInitDeclaration( fileOut, superType ):
	fileOut.write('[super init')
	prefx = "With"
	for fieldName in superType.allFieldNames():
		fieldType = superType.fieldType( fieldName )
		fieldAlias = superType.fieldAlias( fieldName )
		fileOut.write( prefx + capitalizeFirstLetter( fieldAlias ) + ':' + fieldAlias )
		if prefx == "With":
			prefx = '\n' + '\t'*6 + 'and'
	fileOut.write(']')	

def writeOBJCTypeInitDeclaration( fileOut, genType, implementation ):
	fileOut.write('- (instancetype)init')
	prefx = "With"
	for fieldName in genType.allFieldNames():
		fieldType = genType.fieldType(fieldName)
		fieldAlias = genType.fieldAlias(fieldName)
		fileOut.write( prefx + capitalizeFirstLetter(fieldAlias) + ':(' + assumeOBJCType(fieldType) + fieldType.ptr + ')' + fieldAlias )
		if prefx == "With":
			prefx = '\n\tand'
	if not implementation:
		fileOut.write(';\n')

def writeOBJCTypeInitDictDeclaration( fileOut, implementation ):
	fileOut.write('- (instancetype)initWithDictionary:(NSDictionary*)dictionary error:(NSError* __autoreleasing*)error')
	if not implementation:
		fileOut.write(';\n')

def writeOBJCTypeInitDataDeclaration( fileOut, implementation ):
	fileOut.write('- (instancetype)initWithJSONData:(NSData*)jsonData error:(NSError* __autoreleasing*)error')
	if not implementation:
		fileOut.write(';\n')

def writeOBJCTypeDeclaration( fileOut, genType, writeConstructors, writeDump ):
	if isinstance( genType, GenIntegralType ) or isinstance( genType, GenListType ):
		return
	
	if genType.baseType is not None:
		fileOut.write("\n@interface " + genType.name + ": " + genType.baseType.name + "\n")
	else:
		fileOut.write("\n@interface " + genType.name + ": NSObject\n")

	if writeDump:
		fileOut.write("- (NSData*)dumpWithError:(NSError* __autoreleasing*)error;\n")
	if writeConstructors:
		writeOBJCTypeInitDeclaration( fileOut, genType, implementation = False )
		writeOBJCTypeInitDictDeclaration( fileOut, implementation = False )
		writeOBJCTypeInitDataDeclaration( fileOut, implementation = False )	

	for fieldName in genType.fieldNames():
		fieldType = genType.fieldType(fieldName)
		if isinstance( fieldType, GenListType ):
			fileOut.write("@property (nonatomic) " + assumeOBJCType( fieldType ) + fieldType.ptr + '/*' + assumeOBJCType( fieldType.itemType ) + '*/' + " " + genType.fieldAlias( fieldName ) + ";\n")
		else:
			fileOut.write("@property (nonatomic) " + assumeOBJCType( fieldType ) + fieldType.ptr + " " + genType.fieldAlias(fieldName) + ";\n")
	fileOut.write("@end;\n");

def writeOBJCMethodDeclarationArguments( fileOut, formalType, argDecoration, prefix ):
	for argName in formalType.fieldNames():
		argType = formalType.fieldType(argName)
		argAlias = formalType.fieldAlias(argName)
		typeStr = assumeOBJCType( argType )
		fileOut.write( prefix + capitalizeFirstLetter( argAlias ) + ":(" + typeStr + argType.ptr + ")" + argAlias );
		prefix = argDecoration + "and"
	return prefix

def writeOBJCMethodDeclaration( fileOut, method, implementation ):
	argDecoration = " "
	if len(method.customRequestTypes) + len(method.requestJsonType.fieldNames()) > 1:
		argDecoration = "\n\t\t"

	if method.responseType is not None:
		if isinstance( method.responseType, GenListType ):
			fileOut.write("- (" + assumeOBJCType( method.responseType ) + method.responseType.ptr + '/*' + assumeOBJCType( method.responseType.itemType ) + '*/' + ")" + method.name )			
		else:		
			fileOut.write("- (" + assumeOBJCType( method.responseType ) + method.responseType.ptr + ")" + method.name )
	else:
		fileOut.write("- (void)" + method.name )
	
	pref = "With"

	if method.prefix is None:
		fileOut.write( pref + "Prefix:(NSString*)prefix")
		pref = argDecoration + "and"		

	for customRequestParamKey in method.customRequestTypes.keys():
		pref = writeOBJCMethodDeclarationArguments( fileOut, method.customRequestTypes[customRequestParamKey], argDecoration, pref )

	if method.requestJsonType is not None:
		pref = writeOBJCMethodDeclarationArguments( fileOut, method.requestJsonType, argDecoration, pref )

	fileOut.write( pref + "Error:(NSError* __autoreleasing*)error")

	if not implementation:
		fileOut.write(";\n\n");

def decorateOBJCReturnedType( levelTmpVar, objcRetTypeStr, retType ):
	formatNSNumberStr = '( {0} = {1}, [{0} isEqual:[NSNull null]] ? {2} : (({3}){0}).{4} )'
	formatNSStringStr = '( {0} = {1}, [{0} isEqual:[NSNull null]] ? nil : (NSString*){0} )'
	formatNSDictionaryStr = '( {0} = {1}, [{0} isEqual:[NSNull null]] ? nil : (NSDictionary*){0} )'
	formatRawNSDictionaryStr = '( {0} = {1}, [{0} isEqual:[NSNull null]] ? nil : [NSJSONSerialization JSONObjectWithData:[(NSString*){0} dataUsingEncoding:NSUTF8StringEncoding] options:NSJSONReadingAllowFragments error:&error] )'		
	if retType.sType == "bool":
		return formatNSNumberStr.format( levelTmpVar, objcRetTypeStr, 'NO', 'NSNumber*', 'boolValue' )
	if retType.sType == "int32":
		return formatNSNumberStr.format( levelTmpVar, objcRetTypeStr, '0', 'NSNumber*', 'intValue' )
	if retType.sType == "int64":
		return formatNSNumberStr.format( levelTmpVar, objcRetTypeStr, '0L', 'NSNumber*', 'longLongValue' )
	if retType.sType == "double":
		return formatNSNumberStr.format( levelTmpVar, objcRetTypeStr, '0.0', 'NSNumber*', 'doubleValue' )
	if retType.sType == "string":
		return formatNSStringStr.format( levelTmpVar, objcRetTypeStr )
	if retType.sType == "raw":
		return formatNSDictionaryStr.format( levelTmpVar, objcRetTypeStr )
	if retType.sType == "rawstr":
		return formatRawNSDictionaryStr.format( levelTmpVar, objcRetTypeStr )
	return "ERROR";

def unwindReturnedTypeToOBJC( fileOut, objcDictName, outType, outArgName, level, tmpVarName ):

	if isinstance( outType, GenIntegralType ): 	
		if outArgName is None:
			#return ( decorateOBJCReturnedType( tmpVarName, objcDictName, outType ) ) #TODO: fix this strange 'objcDictName' behavior in case of lists unwind
			return objcDictName;
		else:
			return ( decorateOBJCReturnedType( tmpVarName, '[' + objcDictName +  ' objectForKey:@"' + outArgName + '"]', outType ) )

	if isinstance( outType, GenComplexType ):
		objCResType = assumeOBJCType( outType )
		currentDictName = objcDictName
		resName = outType.name + str( newVariableCounter() )	

		if outArgName is None or outArgName != 'self':
			fileOut.write('\t'*level + objCResType + outType.ptr + ' ' + resName + ';\n')
		else:		
			resName = 'self'

		if outArgName is not None and outArgName != 'self':
			currentDictName = objcDictName + capitalizeFirstLetter( outArgName ) + str( newVariableCounter() )
			fileOut.write('\t'*level + 'NSDictionary* ' + currentDictName + ' = [' + objcDictName + ' objectForKey:@"' + outArgName + '"];\n')
			fileOut.write('\t'*level + 'if ( ' + currentDictName + ' != nil && ![' + currentDictName + ' isEqual:[NSNull null]] && [' + currentDictName + ' isKindOfClass:NSDictionary.class]) {\n')
			level += 1
 			fileOut.write( '\t'*level + resName + ' = [' + objCResType + ' new];\n' )
 		elif outArgName != 'self':
 			fileOut.write( '\t'*level + resName + ' = [' + objCResType + ' new];\n' )

#TODO: uncomment after optional arguments appear
#			errMsg = '@"Can`t parse answer from server in ' + outArgName + '"'
#			fileOut.write('\tif ( ' + currentDictName + ' != nil ) {\n\t\tNSLog(' + errMsg +  ');\n')
#			fileOut.write('\t\t*error = [self errorWithMessage:' + errMsg + '];\n')
#			fileOut.write('\t\treturn nil;\n\t}\n')

		for fieldKey in outType.allFieldNames():
			outField = outType.fieldType(fieldKey)
			value = unwindReturnedTypeToOBJC( fileOut, currentDictName, outField, fieldKey, level+1, tmpVarName )
			fileOut.write('\t'*level + resName + '.' + outType.fieldAlias(fieldKey) + ' = ' + value + ';\n')

		if outArgName is not None and outArgName != 'self':
			level -= 1
			fileOut.write('\t'*level + '}\n')

		return resName

	if isinstance( outType, GenListType ):
		if outArgName is None:
			currentArrayName = objcDictName
		else:
			currentArrayName = objcDictName + capitalizeFirstLetter( outArgName ) + str( newVariableCounter() )
			fileOut.write('\t'*level + 'NSArray* ' + currentArrayName + ' = [' + objcDictName + ' objectForKey:@"' + outArgName + '"];\n')

		objCResType = assumeOBJCType( outType )
		if outArgName is not None:
			resName = outArgName + str(level)
		else:
			resName = "array" + str(level)

		fileOut.write('\t'*level + 'NSMutableArray* ' + resName + ';\n')

		fileOut.write('\t'*level + 'if ( ' + currentArrayName + ' != nil && ![' + currentArrayName + ' isEqual:[NSNull null]] && [' + currentArrayName + ' isKindOfClass:NSArray.class]) {\n')
		level += 1

		fileOut.write('\t'*level + resName + ' = [NSMutableArray arrayWithCapacity:[' + currentArrayName + ' count]];\n')

		fileOut.write('\t'*level + 'for ( id item in ' + currentArrayName + ') {\n' )
		item = unwindReturnedTypeToOBJC( fileOut, 'item', outType.itemType, None, level+1, tmpVarName )
		fileOut.write( '\t'*(level+1) + '[' + resName + ' addObject:' + item + '];\n' )
		fileOut.write('\t'*level + '}\n' )

		level -= 1
		fileOut.write('\t'*level + '}\n')

		return resName
					
def decorateOBJCInputType( objcInpTypeStr, inpType ):
	prefix = "NULLABLE("
	suffix = ")"
	if inpType.sType == 'bool':
		prefix = '[NSNumber numberWithBool:'
		suffix = "]"
	if inpType.sType == 'int32':
		prefix = '[NSNumber numberWithInt:'
		suffix = ']'
	if inpType.sType == 'int64':
		prefix = '[NSNumber numberWithLongLong:'
		suffix = ']'
	if inpType.sType == 'double':
		prefix = '[NSNumber numberWithDouble:'
		suffix = ']'
	if inpType.sType == 'rawstr':
		prefix = objcInpTypeStr + ' == nil ? [NSNull null] : [[NSString alloc] initWithData:[NSJSONSerialization dataWithJSONObject:'
		suffix =  ' options:jsonFormatOption error:error] encoding:NSUTF8StringEncoding]'
	return prefix + objcInpTypeStr + suffix

def unwindInputTypeToOBJC( fileOut, inputType, inputArgName, level  ):
		if isinstance( inputType, GenIntegralType ):
			fileOut.write( decorateOBJCInputType( inputArgName, inputType ) )
	
		elif isinstance( inputType, GenComplexType ):
			fileOut.write( "@{\n" )
	
			firstArgument = True
			for argName in inputType.allFieldNames():
				if not firstArgument:
					fileOut.write(",\n")
				firstArgument = False

				fileOut.write( '\t'*level + '@"' + argName + '" : ')
				fieldType = inputType.fieldType(argName)
				objcStatement = inputType.fieldAlias(argName)
				if inputArgName is not None:
					objcStatement = inputArgName + '.' + inputType.fieldAlias(argName)
				unwindInputTypeToOBJC( fileOut, fieldType, objcStatement, level+1 )

			fileOut.write("\n" + '\t'*level + "}")

		elif isinstance( inputType, GenListType ):
			if isinstance( inputType.itemType, GenIntegralType ):
				fileOut.write( 'NULLABLE(' + inputArgName + ')' )
			else:
				fileOut.write('^NSArray*(NSArray* inArr) {\n' + '\t'*level + 'NSMutableArray* resArr = [NSMutableArray arrayWithCapacity:[inArr count]];\n')
				fileOut.write('\t'*level + '\tfor ( ' + assumeOBJCType(inputType.itemType) + inputType.itemType.ptr + ' inObj in inArr ) {\n' ) 
				fileOut.write('\t'*level + '\t\t[resArr addObject:')
				unwindInputTypeToOBJC( fileOut, inputType.itemType, 'inObj', level+2 )
				fileOut.write( '];\n' + '\t'*level + '\t}\n' + '\t'*level + '\treturn resArr; } ( ' + inputArgName + ' )' )

def writeOBJCTypeImplementation( fileOut, genType, writeConstructors, writeDump ):
	if isinstance( genType, GenIntegralType ) or isinstance( genType, GenListType ):
		return		
	fileOut.write("\n@implementation " + genType.name + "\n") 
	
	if writeDump:
		fileOut.write("- (NSData*)dumpWithError:(NSError* __autoreleasing*)error {\n")
		fileOut.write("\tNSDictionary* outDict = ")
		unwindInputTypeToOBJC( fileOut, genType, 'self', 2 )
		fileOut.write(";\n")
		fileOut.write("\treturn [NSJSONSerialization dataWithJSONObject:outDict options:jsonFormatOption error:error];\n}\n")

	if writeConstructors:
		writeOBJCTypeInitDeclaration( fileOut, genType, implementation = True )
		fileOut.write('{\n')
		if genType.baseType is not None:
			fileOut.write('\tif (self = ')
			writeOBJCTypeSuperInitDeclaration( fileOut, genType.baseType )
			fileOut.write(') {\n')
		else:
			fileOut.write('\tif (self = [super init]) {\n')
		
		for fieldName in genType.fieldNames():
			field = genType.fieldType(fieldName)
			fieldAlias = genType.fieldAlias(fieldName)
			fileOut.write('\t\t_' + fieldAlias + ' = ' + fieldAlias + ';\n' )
		fileOut.write('\t}\n\treturn self;\n}\n')

		fileOut.write('- (void)readDictionary:(NSDictionary*)dict {\n')
		fileOut.write('\tid tmp; NSError* error;\n')
		unwindReturnedTypeToOBJC( fileOut, 'dict', genType, 'self', level=1, tmpVarName='tmp' )
		fileOut.write('}\n')

		writeOBJCTypeInitDictDeclaration( fileOut, implementation = True )
		fileOut.write(""" {
	if ( dictionary == nil ) return nil;
	if (self = [super init]) {
		[self readDictionary:dictionary];
	}
	return self;
}
""")

		writeOBJCTypeInitDataDeclaration( fileOut, implementation = True )
		fileOut.write(""" {
	if ( jsonData == nil ) return nil;
	if (self = [super init]) {
		NSDictionary* dict = [NSJSONSerialization JSONObjectWithData:jsonData options:NSJSONReadingAllowFragments error:error];
		if ( error && *error != nil ) return nil;
		[self readDictionary:dict];
	}
	return self;
}
""")

	fileOut.write("@end\n")
			
def writeOBJCMethodCustomRequestParam( fileOut, customRequestParamName, customRequestParam ):
	paramSelectorName = makeAlias( 'set_' + customRequestParamName )
	fileOut.write('\tif (![transport respondsToSelector:@selector(' + paramSelectorName + ':)]) {\n\t\tassert("Transport does not respond to selector ' + paramSelectorName + ':");\n\t} ')
	fileOut.write('else {\n\t\t[transport performSelector:@selector(' + paramSelectorName + ':) withObject:')
	unwindInputTypeToOBJC( fileOut, customRequestParam, None, 3)
	fileOut.write('\n\t\t];\n\t}\n')

def writeOBJCMethodImplementation( fileOut, method ):
	writeOBJCMethodDeclaration( fileOut, method, implementation = True )

	fileOut.write(" {\n")

	tmpVarName = "tmp"
	fileOut.write('\tid ' + tmpVarName + ';\n')

	for customRequestParamKey in method.customRequestTypes.keys():
		writeOBJCMethodCustomRequestParam( fileOut, customRequestParamKey, method.customRequestTypes[customRequestParamKey] )

	methodPrefix = "prefix"
	if method.prefix is not None:
		methodPrefix = '@"' + method.prefix + '"'

	if method.requestJsonType is not None:		
		fileOut.write("\tNSDictionary* inputDict = ")
		unwindInputTypeToOBJC( fileOut, method.requestJsonType, None, 2 )
		
		fileOut.write(";\n")

		fileOut.write("\tNSData* inputData = [NSJSONSerialization dataWithJSONObject:inputDict options:jsonFormatOption error:error];\n")
		fileOut.write('\tif ( ![transport writeAll:inputData prefix:' + methodPrefix + ' error:error] ) {\n')
	else:
		fileOut.write('\tif ( ![transport writeAll:nil prefix:' + methodPrefix + ' error:error] ) {\n')

	# fileOut.write('\t\tNSLog(@"' + method.name + ': server call failed, %@", *error);\n')

	if method.responseType is None:
		fileOut.write('\t\treturn;\n\t}\n')		
		fileOut.write('}\n')
		return
	else:
		fileOut.write('\t\treturn nil;\n\t}\n')

	fileOut.write('\tNSData* outputData = [transport readAll];\n\tif ( outputData == nil ) {\n')
	# fileOut.write('\t\tNSLog(@"' + method.name + ': empty answer");\n\t\treturn nil;\n\t}\n')
	fileOut.write('\t\treturn nil;\n\t}\n')

	outputName = 'output'
	outputStatement = 'id ' + outputName

	fileOut.write('\t' + outputStatement + ' = [NSJSONSerialization JSONObjectWithData:outputData options:NSJSONReadingAllowFragments error:error];\n');
	fileOut.write('\tif ( error && *error != nil ) {\n\t\treturn nil;\n\t}\n')

	retVal = unwindReturnedTypeToOBJC( fileOut, outputName, method.responseType, method.responseArgName, 1, tmpVarName )

	fileOut.write('\treturn ' + retVal + ';\n')	
	fileOut.write("}\n\n")

def writeObjCIfaceHeader( fileOut, inputName ):
	declaration = """
#import <Foundation/Foundation.h>
#import "IFTransport.h"
"""
	fileOut.write(declaration)

def writeObjCIfaceImports( fileOut, importNames ):
	for name in importNames:
		fileOut.write('#import "%s.h"\n' % name)

def writeObjCIfaceDeclaration( fileOut, inputName ):
	declaration = Template("""
@interface $inName: NSObject
- (instancetype)initWithTransport:(id<IFTransport>)transport NS_DESIGNATED_INITIALIZER;
""")
	fileOut.write(declaration.substitute(inName=inputName))

def writeObjCIfaceFooter( fileOut, inputName ):
	fileOut.write("\n@end")

def writeObjCImplHeader( fileOut, inputName ):
	declaration = Template("""\
#import "$inName.h"
#define NULLABLE( s ) (s == nil ? [NSNull null] : s)
static const NSUInteger jsonFormatOption = 
#ifdef DEBUG
	NSJSONWritingPrettyPrinted;
#else
	0;
#endif

#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wunused"
#pragma clang diagnostic ignored "-Wundeclared-selector"

""")
	fileOut.write(declaration.substitute(inName=inputName))

def writeObjCImplDeclaration( fileOut, inputName ):
	declaration = Template("""
@interface $inName() {
	id<IFTransport> transport;
}
@end

@implementation $inName
- (instancetype)initWithTransport:(id<IFTransport>)trans {
	if ( self = [super init] ) {
		transport = trans;
	}
	return self;
}
- (NSError*)errorWithMessage:(NSString*)msg {
	return [NSError errorWithDomain:NSStringFromClass([self class]) code:0 userInfo:@{NSLocalizedDescriptionKey: msg}];
}
""")
	fileOut.write(declaration.substitute(inName=inputName))

def writeObjCImplFooter( fileOut, inputName ):
	fileOut.write("\n@end")	

def writeObjCFooter( fileOut ):
	fileOut.write('\n#pragma clang diagnostic pop\n')

def writeWarning( fileOut, inputName ):
	declaration = """\
/**
 * @generated
 *
 * AUTOGENERATED. DO NOT EDIT! 
 *
 */

"""
	fileOut.write(declaration)

#####################################

def processJSONIface( jsonFile, verbose, typeNamePrefix, outDir, writeFullImplementation ):

	if outDir is not None:
		genDir = os.path.abspath( outDir )

	if typeNamePrefix is not None:
		GenModule.namePrefix = typeNamePrefix
		GenType.namePrefix = typeNamePrefix

	module = parseModule( jsonFile )
	if module is None:
		print("Can't load module " + jsonFile)
		return

	if verbose:
		for genTypeKey in module.typeList.keys():
			print( str( module.typeList[genTypeKey] ) + '\n' )
		for method in module.methods:
			print( str( method ) + '\n' )

	if not os.path.exists( genDir ):
	    os.makedirs( genDir )

	objCIface = open( os.path.join( genDir, module.name + ".h" ), "wt" )
	objCImpl = open( os.path.join( genDir, module.name + ".m" ), "wt" )

	writeWarning( objCIface, None )
	writeWarning( objCImpl, None )

	writeObjCIfaceHeader( objCIface, module.name )
	writeObjCIfaceImports( objCIface, module.importedModuleNames )

	writeObjCImplHeader( objCImpl, module.name )			

	for genTypeKey in module.typeList.keys():
		writeAll = writeFullImplementation or ( genTypeKey in module.structs )						
		writeOBJCTypeDeclaration( objCIface, module.typeList[genTypeKey], writeDump=writeAll, writeConstructors=writeAll )
		writeOBJCTypeImplementation( objCImpl, module.typeList[genTypeKey], writeDump=writeAll, writeConstructors=writeAll )

	if len( module.methods ) != 0:
		writeObjCIfaceDeclaration( objCIface, module.name )
		writeObjCImplDeclaration( objCImpl, module.name )
		objCIface.write("\n/* methods */\n\n")
		objCImpl.write("\n/* implementation */\n\n")	

	for method in module.methods:
		writeOBJCMethodDeclaration( objCIface, method, implementation = False )
		writeOBJCMethodImplementation( objCImpl, method )

	if len( module.methods ) != 0:
		writeObjCIfaceFooter( objCIface, module.name )
		writeObjCImplFooter( objCImpl, module.name )

	writeObjCFooter( objCImpl )

def main():
	parser = argparse.ArgumentParser(description='JSON-ObjC interface generator')
	
	parser.add_argument('rpcInput', metavar='I', type=unicode, nargs = '+', help = 'Input JSON RPC files')
	parser.add_argument('--prefix', action='store', required=False, help='Class and methods prefix')
	parser.add_argument('--writefull', action='store_true', required=False, help='Indicates that it is needed to write full set of initializers for all the structs found in IDL')
	parser.add_argument('--verbose', action='store_true', required=False, help='Verbose mode')
	parser.add_argument('-o', '--outdir', action='store', default="gen-objc", required=False, help="Output directory name")

	parsedArgs = parser.parse_args()
	if len(sys.argv) == 1:
	    parser.print_help()
	    return 0

	try:
		for rpcInput in parsedArgs.rpcInput:
			processJSONIface( rpcInput, parsedArgs.verbose, parsedArgs.prefix, parsedArgs.outdir, parsedArgs.writefull )
	except Exception as ex:
		print( str(ex) )
		sys.exit(1)

	return 0

#########

if __name__ == "__main__":
	main()
	