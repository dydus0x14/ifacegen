//
//  ifacegen_test_test.swift
//  ifacegen.test.test
//
//  Created by Evgeny Kamyshanov on 22.11.14.
//  Copyright (c) 2014 ptiz. All rights reserved.
//

import Cocoa
import XCTest

class ifacegen_test_test: XCTestCase {

    var pass:OBCEmployeePassport!
    var employee0:OBCEmployee!
    var employee1:OBCEmployee!
    var employer:OBCEmployer!
    
    var swPassport: EmployeePassport!
    var swEmployee1: Employee!
    var swEmployee2: Employee!
    var swEmployee3: Employee!
    var swEmployer: Employer!
    
    override func setUp() {
        super.setUp()
        
        pass = OBCEmployeePassport()
        pass.theId = 786234
        pass.organization = "10 OM"

        let child = OBCEmployeeChildrenItem()
        child.name = "Mary"
        child.birthdate = Int64(NSDate().timeIntervalSince1970)
        
        employee0 = OBCEmployee(name: "empl0", andTheId: 781341234, andDimension: 345.67, andPassport: self.pass, andChildren:[child])
        employee1 = OBCEmployee(name: "empl1", andTheId: 87245, andDimension: 623.76, andPassport: self.pass, andChildren:[child, child])
        employer = OBCEmployer(stuff: [self.employee0, self.employee1], andInfo: ["review":"passed"])
        
        //------------------
        swPassport = EmployeePassport()
        swPassport.theId = 123456789
        swPassport.organization = "Org"
        
        let swChild = EmployeeChildrenItem()
        swChild.name = "Name"
        swChild.birthdate = Int(NSDate().timeIntervalSince1970)
        
        swEmployee1 = Employee(name: "swEmp1", theId: 1111, dimension: 0.8, passport: swPassport, children: nil)
        swEmployee2 = Employee(name: "swEmp2", theId: 111143, dimension: 10.8, passport: swPassport, children: [])
        swEmployee3 = Employee(name: "swEmp3", theId: 1111432, dimension: 101.8, passport: swPassport, children: [swChild, swChild, swChild])
        swEmployer = Employer(stuff: [swEmployee1, swEmployee2, swEmployee3], info: ["review":"passed"])
    }
    
    override func tearDown() {
        super.tearDown()
    }
    
    func testSerialization() {
        
        var error:NSError?
        let data = self.employer.dumpWithError(&error)
        
        XCTAssertNil(error, "Serialization was unsuccessful")
        
        let desEmployer = OBCEmployer(JSONData: data, error: &error)
        
        XCTAssertEqual(desEmployer.stuff.count, 2, "Data was not deserialized successfully")
        
        let desEmployee0 = desEmployer.stuff[0] as OBCEmployee
        let desEmployee1 = desEmployer.stuff[1] as OBCEmployee
        
        XCTAssertEqual(desEmployee0.name, "empl0", "Employee.name is wrong")
        XCTAssertTrue(desEmployee0.passport.theId == 786234, "Employee pass is wrong")
        XCTAssertTrue(desEmployee0.children.count == 1, "Children0 array is wrong" )
        XCTAssertTrue(desEmployee1.children.count == 2, "Children1 array is wrong")
        
        let desChild = desEmployee1.children[1] as OBCEmployeeChildrenItem
        XCTAssertEqual(desChild.name, "Mary", "Child name is wrong")
    }
    
    func testSwiftSerealization() {
        var error:NSError?
        let data = self.swEmployer.dumpWithError(&error)
        
        XCTAssertNil(error, "Serialization was unsuccessful")
        
        let desEmployer = Employer(jsonData: data, error: &error)
        
        XCTAssertEqual(desEmployer!.stuff.count, 3, "Data was not deserialized successfully")
        
        let desEmployee1 = desEmployer!.stuff[0] as Employee
        let desEmployee2 = desEmployer!.stuff[1] as Employee
        let desEmployee3 = desEmployer!.stuff[2] as Employee
        
        XCTAssertEqual(desEmployee1.name, "swEmp1", "Employee.name is wrong")
        XCTAssertTrue(desEmployee1.passport.theId == 123456789, "Employee pass is wrong")
        XCTAssertTrue(desEmployee1.children == nil, "Children0 array is wrong" )
        XCTAssertTrue(desEmployee2.children.count == 0, "Children1 array is wrong")
        XCTAssertTrue(desEmployee3.children.count == 3, "Children2 array is wrong")
        
        let desChild = desEmployee3.children[1] as EmployeeChildrenItem
        XCTAssertEqual(desChild.name, "Name", "Child name is wrong")
    }
    
}
