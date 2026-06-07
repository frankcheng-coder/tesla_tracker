import Foundation
import SwiftUI

/// Selects which API client backs the app.
enum APIMode {
    case mock
    case live(URL)

    static var `default`: APIMode {
        // Point at a running backend by setting this to `.live(...)`.
        // Defaults to mock so the app runs with no server (build step 5).
        .mock
    }
}

@MainActor
final class AppEnvironment: ObservableObject {
    @Published var isConnected: Bool
    @Published var selectedVehicle: Vehicle?
    @Published var vehicles: [Vehicle] = []
    @Published var trackingPaused: Bool = false

    let api: TripAPI

    init(mode: APIMode = .default) {
        switch mode {
        case .mock:
            self.api = MockAPIClient()
        case .live(let url):
            self.api = LiveAPIClient(baseURL: url)
        }
        // Persisted connection state across launches.
        self.isConnected = UserDefaults.standard.bool(forKey: "isConnected")
    }

    func markConnected() {
        isConnected = true
        UserDefaults.standard.set(true, forKey: "isConnected")
    }

    func disconnect() {
        isConnected = false
        selectedVehicle = nil
        UserDefaults.standard.set(false, forKey: "isConnected")
    }

    func loadVehicles() async {
        do {
            vehicles = try await api.vehicles()
            if selectedVehicle == nil { selectedVehicle = vehicles.first }
        } catch {
            vehicles = []
        }
    }
}
