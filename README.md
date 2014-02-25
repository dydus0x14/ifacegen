# ifacegen

## What it is
ifacegen is a code generator, it simplifies using of existing REST+JSON APIs from Objective-C code. ifacegen makes native wrappers for remote service calls and JSON dictionaries. Simple IDL used for description of existing protocol.

## What is not
ifacegen is not general purpose serialization tool. It's only compiles IDL given and generates special Objective-C classes accordingly. ifacegen doesn't support JSON Schema because of it's verbosity.

##Requirements
iOS+ARC, Python 2.7

##Limitations
- For ARC only;
- NSJSONSerialization used in generated code for JSON data creation, so there is intermediate dictionary created before a data writing in a transport;
- You can not define global prefix for all the structs in generated code yet;
- No "date", "enum" etc. in atomic IDL types. Only int32, int64, double, string, bool, raw и rawstr. "raw" will be converted in NSDictionary from JSON dictionary and "rawstr" — in NSDictionary from JSON dictionary encoded in string (like this: "data": "{\"weird\":42,\"str\":\"yes\"}");
- No types importing from other IDL modules;
- No forwarding struct declaration;
- No readable error messages for parser and generator yet.

##Usage
Example included. Tutorial see in repo wiki: https://bitbucket.org/ifreefree/ifacegen/wiki/Home