import SwiftUI

@main
struct TeslaTripLoggerApp: App {
    @StateObject private var env = AppEnvironment()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(env)
        }
    }
}

struct RootView: View {
    @EnvironmentObject var env: AppEnvironment

    var body: some View {
        Group {
            if !env.isConnected {
                OnboardingView()
            } else if env.selectedVehicle == nil {
                VehicleSelectionView()
            } else {
                MainTabView()
            }
        }
        .task { await env.loadVehicles() }
    }
}

struct MainTabView: View {
    var body: some View {
        TabView {
            TripHistoryView()
                .tabItem { Label("Trips", systemImage: "list.bullet.rectangle") }
            MapHistoryView()
                .tabItem { Label("Map", systemImage: "map") }
            SettingsView()
                .tabItem { Label("Settings", systemImage: "gearshape") }
        }
    }
}
