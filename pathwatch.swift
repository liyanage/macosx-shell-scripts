#!/usr/bin/swift

//
//  main.swift
//  pathwatch
//
//  Created by Marc Liyanage on 10/19/19.
//  Copyright © 2019 Marc Liyanage. All rights reserved.
//

import Foundation

let args = CommandLine.arguments
let firstPathArgumentIndex = 1
let lastPathArgumentIndex = args.count - 2
let shellCommandArgumentIndex = args.count - 1

guard shellCommandArgumentIndex >= 2 else {
    print("Usage: \(args[0]) <path to watch> [<path to watch>...] <shell command to execute on change>")
    exit(1)
}

let commandString = args[shellCommandArgumentIndex]

let allPathsDataSource = DispatchSource.makeUserDataAddSource()
allPathsDataSource.setEventHandler {
    print("Running \(commandString)")
    let process = Process()
    process.launchPath = "/bin/sh"
    process.arguments = ["-c", commandString]
    process.launch()
    process.waitUntilExit()
    print("Done running \(commandString)")
}
allPathsDataSource.activate()

var sources = [DispatchSourceFileSystemObject]()
for i in firstPathArgumentIndex...lastPathArgumentIndex {
    let path = args[i]

    var isDir: ObjCBool = false
    let exists = FileManager.default.fileExists(atPath: path, isDirectory: &isDir)
    guard exists else {
        print("Input path does not exist, ignoring: \(path)")
        continue
    }
    
    print("Watching \(isDir.boolValue ? "directory" : "file") \(path)")
    let fd = open(path, O_EVTONLY)
    let fileSystemPathSource = DispatchSource.makeFileSystemObjectSource(fileDescriptor: fd, eventMask: .attrib)
    var lastContentHash: Int = 0
    fileSystemPathSource.setEventHandler {
        sleep(1)
        if !isDir.boolValue {
            let data = try! Data(contentsOf: URL(fileURLWithPath: path))
            let newContentHash = data.hashValue
            guard newContentHash != lastContentHash else {
                print("Ignoring file system event for path with unchanged content: \(path)")
                return
            }
            lastContentHash = newContentHash
        }
        print("File system change event for \(path)")
        allPathsDataSource.add(data: 1)
    }
    fileSystemPathSource.setCancelHandler {
        close(fd)
    }
    sources.append(fileSystemPathSource)
    fileSystemPathSource.activate()
}

dispatchMain()

