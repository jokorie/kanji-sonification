//
//  KanjiSonificationApp.swift
//  KanjiSonification
//
//  Main app entry point for the Kanji Sonification iOS app.
//

import SwiftUI

@main
struct KanjiSonificationApp: App {
    @StateObject private var oscManager = OSCManager()
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(oscManager)
        }
    }
}

