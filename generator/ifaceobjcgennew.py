from ifaceparser import *
import argparse
import sys
import types
import os
from collections import OrderedDict
from string import Template

#TODO: rename to OBJCAssumeType
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

def OBJCDecorateTypeForDict( objcTypeStr, genType ):
	template = Template('NULLABLE($objcTypeStr)')
	if genType.sType == 'bool' or genType.sType == 'int32' or genType.sType == 'int64' or genType.sType == 'double':
		template = Template('@($objcTypeStr)')
	if genType.sType == 'rawstr':
		template = Template('[[NSString alloc] initWithData:[NSJSONSerialization dataWithJSONObject:$objcTypeStr options:jsonFormatOption error:error] encoding:NSUTF8StringEncoding]')
	return template.substitute( objcTypeStr=objcTypeStr )

def OBJCDecorateTypeFromJSON( retType, varValue ):
	templateNSNumberStr = Template('( tmp = $tmpVarValue, [tmp isEqual:[NSNull null]] ? $emptyVal : ((NSNumber*)tmp).$selector )')
	templateNSStringStr = Template('( tmp = $tmpVarValue, [tmp isEqual:[NSNull null]] ? nil : (NSString*)tmp )')
	templateNSDictionaryStr = Template('( tmp = $tmpVarValue, [tmp isEqual:[NSNull null]] ? nil : (NSDictionary*)tmp )')
	templateRawNSDictionaryStr = Template('( tmp = $tmpVarValue, [tmp isEqual:[NSNull null]] ? nil : [NSJSONSerialization JSONObjectWithData:[(NSString*)tmp dataUsingEncoding:NSUTF8StringEncoding] options:NSJSONReadingAllowFragments error:&error] )')
	if retType.sType == "bool":
		return templateNSNumberStr.substitute( tmpVarValue=varValue, emptyVal='NO', selector='boolValue' )
	if retType.sType == "int32":
		return templateNSNumberStr.substitute( tmpVarValue=varValue, emptyVal='0', selector='intValue' )
	if retType.sType == "int64":
		return templateNSNumberStr.substitute( tmpVarValue=varValue, emptyVal='0L', selector='longLongValue' )
	if retType.sType == "double":
		return templateNSNumberStr.substitute( tmpVarValue=varValue, emptyVal='0.0', selector='doubleValue' )
	if retType.sType == "string":
		return templateNSStringStr.substitute( tmpVarValue=varValue )
	if retType.sType == "raw":
		return templateNSDictionaryStr.substitute( tmpVarValue=varValue )
	if retType.sType == "rawstr":
		return templateRawNSDictionaryStr.substitute( tmpVarValue=varValue )
	return "ERROR";


def OBJCAppendIfNotEmpty( list, strItem ):
	if strItem is not None and len(strItem) > 0:
		list.append( strItem )

############################
# Header declaration
############################

def OBJCArgList( genType ):
	template = Template('$arg:($argType$argTypePtr)$argAlias')
	argList = []
	for fieldName in genType.allFieldNames():
		fieldType = genType.fieldType(fieldName)
		fieldAlias = genType.fieldAlias(fieldName)
		argList.append( template.substitute( arg=capitalizeFirstLetter(fieldAlias), argType=assumeOBJCType(fieldType), argTypePtr=fieldType.ptr, argAlias=fieldAlias ) )
	return '\n\tand'.join(argList)

def OBJCTypeInitDeclaration( genType ):
	return Template('- (instancetype)initWith$argList').substitute( argList=OBJCArgList( genType ) )

def OBJCTypeSerializersDeclarationList( genType ):
	return """\
- (instancetype)initWithDictionary:(NSDictionary*)dictionary error:(NSError* __autoreleasing*)error;
- (instancetype)initWithJSONData:(NSData*)jsonData error:(NSError* __autoreleasing*)error;
- (NSDictionary*)dictionaryWithError:(NSError* __autoreleasing*)error;
- (NSData*)dumpWithError:(NSError* __autoreleasing*)error;"""

def OBJCTypePropertyList( genType ):
	template = Template('@property (nonatomic) $propType$propTypePtr $propAlias;')
	listTemplate = Template('@property (nonatomic) $propType$propTypePtr/*$itemType*/ $propAlias;')
	propList = []
	for fieldName in genType.fieldNames():
		fieldType = genType.fieldType(fieldName)
		if isinstance( fieldType, GenListType ):
			propList.append( listTemplate.substitute(propType=assumeOBJCType( fieldType ), propTypePtr=fieldType.ptr, itemType=assumeOBJCType( fieldType.itemType ), propAlias=genType.fieldAlias( fieldName )) )
		else:
			propList.append( template.substitute(propType=assumeOBJCType( fieldType ), propTypePtr=fieldType.ptr, propAlias=genType.fieldAlias( fieldName )) )
	return '\n'.join(propList)

def OBJCTypeDeclaration( genType, serializersListGenerator ):
	if isinstance( genType, GenIntegralType ) or isinstance( genType, GenListType ):
		return ''
	
	baseTypeName = 'NSObject'
	if genType.baseType is not None:
		baseTypeName = genType.baseType.name

	template = Template("""\
@interface $typeName: $baseTypeName
$init;
$serializers
$properties
@end
""")

	return template.substitute(typeName=genType.name, baseTypeName=baseTypeName, init=OBJCTypeInitDeclaration( genType ), serializers=serializersListGenerator( genType ), properties=OBJCTypePropertyList( genType ))

def OBJCTypeForwardingDeclaration( genType ):
	return '@class %s;\n' % genType.name;

def OBJCImportList( module ):
	template = Template('#import "$modImport.h"\n')
	importList = ''
	for name in module.importedModuleNames:
		importList += template.substitute(modImport=name)
	return importList

def OBJCFindDependenciesUnresolved( typeSet, typeToCheck ):
	unresolved = []
	if isinstance( typeToCheck, GenComplexType ):
		for fieldName in typeToCheck.allFieldNames():
			fieldType = typeToCheck.fieldType(fieldName)
			if isinstance( fieldType, GenComplexType ) and ( fieldType.name not in typeSet ):
				unresolved.append( fieldType )
	return unresolved

def OBJCTypeDeclarationList( module, serializersListGenerator ):
	declList = []
	alreadyDeclaredTypes = set( module.importedTypeList.keys() )
	for genTypeName in module.typeList.keys():
		currentType = module.typeList[genTypeName]
		alreadyDeclaredTypes.add( genTypeName )
		for forwardingType in OBJCFindDependenciesUnresolved( alreadyDeclaredTypes, currentType ):
			declList.append( OBJCTypeForwardingDeclaration( forwardingType ) )
		OBJCAppendIfNotEmpty( declList, OBJCTypeDeclaration( currentType, serializersListGenerator ) )
	return '\n'.join( declList )

OBJCGeneratedWarning = """\
/**
 * @generated
 *
 * AUTOGENERATED. DO NOT EDIT! 
 *
 */"""

OBJCHeaderTemplate = Template("""\
$generatedWarning

#import <Foundation/Foundation.h>
#import "IFTransport.h"
#import "IFServiceClient.h"
$importList
$typeDeclarationList
""")

def OBJCHeader( module ):
	return OBJCHeaderTemplate.substitute( generatedWarning=OBJCGeneratedWarning, importList=OBJCImportList( module ), typeDeclarationList=OBJCTypeDeclarationList( module, OBJCTypeSerializersDeclarationList ) )

def OBJCHeaderForCategory( module ):
	return OBJCHeaderTemplate.substitute( generatedWarning=OBJCGeneratedWarning, importList=OBJCImportList( module ), typeDeclarationList=OBJCTypeDeclarationList( module, lambda genType: '' ) )

############################
# Implementation module
############################

def OBJCTypeFieldInitList( genType ):
	template = Template('\t\t_$fieldAlias = $fieldAlias;')
	fieldList = []
	for fieldName in genType.fieldNames():
		field = genType.fieldType(fieldName)
		fieldAlias = genType.fieldAlias(fieldName)
		fieldList.append( template.substitute( fieldAlias=fieldAlias ) )
	return '\n'.join( fieldList )

def OBJCTypeMethodActualArgList( genType ):
	argList = []
	for fieldName in genType.allFieldNames():
		fieldType = genType.fieldType( fieldName )
		fieldAlias = genType.fieldAlias( fieldName )
		argList.append( '%s:%s' % ( capitalizeFirstLetter( fieldAlias ), fieldAlias ) )
	return '\n\t\t\t\t\t\tand'.join( argList )

def OBJCTypeInitImplList( genType ):
	baseTemplate = Template("""
$declaration {
	if (self=[super init]) {
$fieldInitList
	}
	return self;
}""")

	superTemplate = Template("""
$declaration {
	if (self = [super initWith$actualArgList]) {
$fieldInitList
	}
	return self;
}""")
	if genType.baseType is not None:
		return superTemplate.substitute( declaration=OBJCTypeInitDeclaration( genType ), actualArgList=OBJCTypeMethodActualArgList( genType.baseType ), fieldInitList=OBJCTypeFieldInitList( genType ) )
	return baseTemplate.substitute( declaration=OBJCTypeInitDeclaration( genType ), fieldInitList=OBJCTypeFieldInitList( genType ) )

def OBJCUnwindTypeToDict( genType, objcArgName, level, recursive=True ):
	if isinstance( genType, GenIntegralType ):
		return OBJCDecorateTypeForDict( objcArgName, genType )

	elif isinstance( genType, GenComplexType ):
		if not recursive:
			return '[%s dictionaryWithError:error]' % objcArgName

		fieldTemplate = Template('$tabLevel@"$argName":$argValue')
		fieldList = []

		for argName in genType.allFieldNames():
			fieldType = genType.fieldType(argName)
			objcStatement = genType.fieldAlias(argName)
			if objcArgName is not None:
				objcStatement = '%s.%s' % ( objcArgName, genType.fieldAlias(argName) )
			fieldList.append( fieldTemplate.substitute( tabLevel='\t'*level, argName=argName, argValue=OBJCUnwindTypeToDict( fieldType, objcStatement, level+1, recursive=False ) ) )

		return Template('@{\n$fieldList\n$tabLevel}').substitute( fieldList=',\n'.join(fieldList), tabLevel='\t'*(level-1) )

	elif isinstance( genType, GenListType ):
		if isinstance( genType.itemType, GenIntegralType ):
			return 'NULLABLE(%s)' % (objcArgName)
		else:
			arrayTemplate = Template("""\
^NSArray*(NSArray* inArr) {
${tabLevel}NSMutableArray* resArr = [NSMutableArray arrayWithCapacity:[inArr count]];
${tabLevel}for($objcType$objcTypePtr inObj in inArr) { [resArr addObject:$argValue]; }
${tabLevel}return resArr; } ($objcArgName)""")
			return arrayTemplate.substitute( tabLevel='\t'*level, objcType=assumeOBJCType(genType.itemType), objcTypePtr=genType.itemType.ptr, argValue=OBJCUnwindTypeToDict( genType.itemType, 'inObj', level+2, recursive=False ), objcArgName=objcArgName )

def OBJCListTypeFromDictionary( genType, objcDataGetter, level ):
	listTypeTemplate = Template("""\
^NSArray*(id inObj) {
${tabLevel}\tNSMutableArray* items;
${tabLevel}\tif ( inObj == nil ||  [inObj isEqual:[NSNull null]] || ![inObj isKindOfClass:NSArray.class]) return nil;
${tabLevel}\tNSArray* inArr = (NSArray*)inObj;
${tabLevel}\titems = [NSMutableArray arrayWithCapacity:inArr.count];
${tabLevel}\tfor ( id item in inArr ) { id tmp; [items addObject:$itemObj]; }
${tabLevel}\treturn items;
${tabLevel}}( $objcDataGetter )""")
	return listTypeTemplate.substitute( tabLevel='\t'*level, itemObj=OBJCTypeFromDictionary(genType.itemType, "item", level+1 ), objcDataGetter=objcDataGetter )

def OBJCTypeFromDictionary( genType, objcDataGetter, level ):
	complexTypeTemplate = Template('[[$typeName alloc] initWithDictionary:$objcDataGetter error:error]')
	if isinstance( genType, GenIntegralType ):
		return OBJCDecorateTypeFromJSON( genType, objcDataGetter )
	if isinstance( genType, GenComplexType ):
		return complexTypeTemplate.substitute( typeName=genType.name, objcDataGetter=objcDataGetter )
	if isinstance( genType, GenListType ):
		if isinstance(genType.itemType, GenIntegralType):
			return objcDataGetter
		else:
			return OBJCListTypeFromDictionary( genType, objcDataGetter, level+1 )

def OBJCComplexTypeFieldListFromDictionary( genType, objcDictArgName ):
	template = Template('\tself.$argName = $value')
	fieldList = []
	for fieldName in genType.allFieldNames():
		fieldType = genType.fieldType(fieldName)
		objcDataGetter = '%s[@"%s"]' % ( objcDictArgName, fieldName )
		fieldList.append( template.substitute( argName=genType.fieldAlias(fieldName), value=OBJCTypeFromDictionary( fieldType, objcDataGetter, 1 ) ) )
	return ';\n'.join( fieldList )

def OBJCTypeSerializationImplList( genType ):
	template = Template("""
- (NSDictionary*)dictionaryWithError:(NSError* __autoreleasing*)error {
	return $typeDictionary;
}

- (NSData*)dumpWithError:(NSError* __autoreleasing*)error {
	NSDictionary* dict = [self dictionaryWithError:error];
	if (*error) return nil;
	else return [NSJSONSerialization dataWithJSONObject:[self dictionaryWithError:error] options:jsonFormatOption error:error];
}

- (void)readDictionary:(NSDictionary*)dict withError:(NSError* __autoreleasing*)error {
	id tmp;
$complexTypeFieldsFromDictionary;
}
//TODO: check here the super-type proper init with dictionary
- (instancetype)initWithDictionary:(NSDictionary*)dictionary error:(NSError* __autoreleasing*)error {
	if ( dictionary == nil ) return nil;
	if (self = [super init]) {
		[self readDictionary:dictionary withError:error];
		if ( error && *error != nil ) self = nil;
	}
	return self;
}

- (instancetype)initWithJSONData:(NSData*)jsonData error:(NSError* __autoreleasing*)error {
	if ( jsonData == nil ) return nil;
	if (self = [super init]) {
		NSDictionary* dict = [NSJSONSerialization JSONObjectWithData:jsonData options:NSJSONReadingAllowFragments error:error];
		if ( error && *error != nil ) { self = nil; return nil; }
		[self readDictionary:dict withError:error];
		if ( error && *error != nil ) self = nil;
	}
	return self;	
}
""")
	
	return template.substitute( typeDictionary=OBJCUnwindTypeToDict( genType, 'self', 2 ), complexTypeFieldsFromDictionary=OBJCComplexTypeFieldListFromDictionary( genType,'dict' ) )
	
def OBJCTypeImplementation( genType ):
	if isinstance( genType, GenIntegralType ) or isinstance( genType, GenListType ):
		return ''
	template = Template("""\
@implementation $typeName
$initImplList
$serializationImplList
@end
""")
	return template.substitute( typeName=genType.name, initImplList=OBJCTypeInitImplList(genType), serializationImplList=OBJCTypeSerializationImplList(genType) )

def OBJCTypeImplementationForCategory( genType ):
	if isinstance( genType, GenIntegralType ) or isinstance( genType, GenListType ):
		return ''
	template = Template("""\
@implementation $typeName
$initImplList
@end
""")
	return template.substitute( typeName=genType.name, initImplList=OBJCTypeInitImplList(genType) )

def OBJCTypeImplementationList( module, implGenerator ):
	implList = []
	for genTypeName in module.typeList.keys():
		currentType = module.typeList[genTypeName]
		OBJCAppendIfNotEmpty( implList, implGenerator( currentType ) )
	return '\n'.join( implList )

def OBJCModule( module ):
	template = Template("""\
$generatedWarning

#import "$modHeader.h"

#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wunused"
#pragma clang diagnostic ignored "-Wundeclared-selector"

#define NULLABLE( s ) (s == nil ? [NSNull null] : s)
static const NSUInteger jsonFormatOption = 
#ifdef DEBUG
	NSJSONWritingPrettyPrinted;
#else
	0;
#endif

$typeImplementationList

#pragma clang diagnostic pop
""")
	return template.substitute(generatedWarning=OBJCGeneratedWarning, modHeader=module.name, typeImplementationList=OBJCTypeImplementationList( module, OBJCTypeImplementation ))

def OBJCModuleForCategory( module ):
	template = Template("""
$generatedWarning

#import "$modHeader.h"

$typeImplementationList
""")
	return template.substitute(generatedWarning=OBJCGeneratedWarning, modHeader=module.name, typeImplementationList=OBJCTypeImplementationList( module, OBJCTypeImplementationForCategory ))

############################
# Entry point
############################

def writeObjCImplementationMonolith( genDir, module ):
	objCIface = open( os.path.join( genDir, module.name + ".h" ), "wt" )
	objCImpl = open( os.path.join( genDir, module.name + ".m" ), "wt" )

	objCIface.write( OBJCHeader( module ) )
	objCImpl.write( OBJCModule( module ) )

def writeObjCImplementationCategory( genDir, category, module ):
	objCIface = open( os.path.join( genDir, module.name + ".h" ), "wt" )
	objCImpl = open( os.path.join( genDir, module.name + ".m" ), "wt" )
	objCIfaceCategory = open( os.path.join( genDir, module.name + "+" + category + ".h" ), "wt" )
	objCImplCategory = open( os.path.join( genDir, module.name + "+" + category + ".m" ), "wt" )

	objCIface.write( OBJCHeaderForCategory( module ) )
	objCImpl.write( OBJCModuleForCategory( module ) )

def writeObjCImplementation( genDir, category, module ):

	if not os.path.exists( genDir ):
	    os.makedirs( genDir )

	if category is not None and len(category) > 0:
		writeObjCImplementationCategory( genDir, category, module )
	else:
		writeObjCImplementationMonolith( genDir, module )


