//
//  ifacegen_swift_test.swift
//  ifacegen.test
//
//  Created by Anton Davydov on 11/25/14.
//
//

import UIKit
import XCTest

class ifacegen_swift_test: XCTestCase {
    
    var swPassport: EmployeePassport!
    var swEmployee1: Employee!
    var swEmployee2: Employee!
    var swEmployee3: Employee!
    var swEmployer: Employer!
    var dictionary: [String : AnyObject]!
    
    override func setUp() {
        super.setUp()
        
        let bundle = NSBundle(forClass: ifacegen_swift_test.classForCoder())
        let path = bundle.pathForResource("JSONDictionaryTest", ofType: "json")
        let data =  NSData(contentsOfFile: path!)
        dictionary = NSJSONSerialization.JSONObjectWithData(data!, options: .AllowFragments, error: nil) as [String : AnyObject]
        
        swPassport = EmployeePassport()
        swPassport.theId = 123456789
        swPassport.organization = "Org"
        
        let swChild = EmployeeChildrenItem()
        swChild.name = "Name"
        swChild.birthdate = Int64(NSDate().timeIntervalSince1970)
        swEmployee1 = Employee(dictionaryFromRawStr: nil, dictionaryFromRaw: nil, name: "swEmp1", theId: 1111, dimension: 0.8, passport: swPassport, children: nil)
        swEmployee2 = Employee(dictionaryFromRawStr: [:], dictionaryFromRaw: [:], name: "swEmp2", theId: 111143, dimension: 10.8, passport: swPassport, children: [])
        swEmployee3 = Employee(dictionaryFromRawStr: dictionary, dictionaryFromRaw: dictionary, name: "swEmp3", theId: 1111432, dimension: 101.8, passport: swPassport, children: [swChild, swChild, swChild])
        swEmployer = Employer(stuff: [swEmployee1, swEmployee2, swEmployee3], info: ["review":"passed"])
    }
    
    override func tearDown() {
        super.tearDown()
    }
    
    func testSwiftSerealization() {
        var error:NSError?
        let data = self.swEmployer.dump(&error)
        
        XCTAssertNil(error, "Serialization was unsuccessful")
        
        let desEmployer = Employer(jsonData: data, error: &error)
        
        XCTAssertEqual(desEmployer!.stuff!.count, 3, "Data was not deserialized successfully")
        
        let desEmployee1 = desEmployer!.stuff![0]
        let desEmployee2 = desEmployer!.stuff![1]
        let desEmployee3 = desEmployer!.stuff![2]
        
        XCTAssertEqual(desEmployee1.name!, "swEmp1", "Employee.name is wrong")
        XCTAssertTrue(desEmployee1.dictionaryFromRawStr == nil, "RawStr don't work" )
        XCTAssertTrue(desEmployee1.dictionaryFromRaw == nil, "Raw don't work" )
        XCTAssertTrue(desEmployee1.passport!.theId == 123456789, "Employee pass is wrong")
        XCTAssertTrue(desEmployee1.children == nil, "Children0 array is wrong" )
        
        XCTAssertTrue(desEmployee2.children!.count == 0, "Children1 array is wrong")
        XCTAssertTrue(desEmployee2.dictionaryFromRawStr!.isEmpty, "RawStr don't work" )
        XCTAssertTrue(desEmployee2.dictionaryFromRaw!.isEmpty, "Raw don't work" )
        
        XCTAssertTrue(desEmployee3.children!.count == 3, "Children2 array is wrong")
        XCTAssertTrue(desEmployee3.dictionaryFromRawStr?.description == self.dictionary.description, "RawStr don't work" )
        XCTAssertTrue(desEmployee3.dictionaryFromRaw?.description == self.dictionary.description, "Raw don't work" )
        
        let desChild = desEmployee3.children![1] as EmployeeChildrenItem
        XCTAssertEqual(desChild.name!, "Name", "Child name is wrong")
    }
    
}
