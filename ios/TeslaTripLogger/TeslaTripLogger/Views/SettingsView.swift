import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var env: AppEnvironment
    @State private var showDeleteConfirm = false
    @State private var showExportSheet = false
    @State private var zones: [PrivacyZone] = []

    private var appVersion: String {
        let v = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.1.0"
        let b = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "1"
        return "\(v) (\(b))"
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Connected account") {
                    LabeledContent("Tesla account", value: "Connected")
                    if let vehicle = env.selectedVehicle {
                        LabeledContent("Vehicle", value: vehicle.name)
                        LabeledContent("VIN", value: vehicle.vin)
                    }
                }

                Section("Tracking") {
                    Toggle("Pause tracking", isOn: $env.trackingPaused)
                    Text(env.trackingPaused
                         ? "Tracking is paused. No new location points are recorded."
                         : "Tracking is active. New trips are recorded read-only.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Section("Privacy zones") {
                    if zones.isEmpty {
                        Text("No privacy zones yet.")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(zones) { zone in
                            VStack(alignment: .leading) {
                                Text(zone.name).font(.headline)
                                Text(zone.hideExactLocation
                                     ? "Exact location hidden · \(Int(zone.radiusMeters)) m"
                                     : "\(Int(zone.radiusMeters)) m radius")
                                    .font(.caption).foregroundStyle(.secondary)
                            }
                        }
                    }
                    NavigationLink("Add privacy zone") { AddPrivacyZonePlaceholder() }
                }

                Section("Data") {
                    Button {
                        showExportSheet = true
                    } label: {
                        Label("Export CSV", systemImage: "square.and.arrow.up")
                    }
                    Button(role: .destructive) {
                        showDeleteConfirm = true
                    } label: {
                        Label("Delete all trip history", systemImage: "trash")
                    }
                }

                Section {
                    Button(role: .destructive) {
                        env.disconnect()
                    } label: {
                        Text("Disconnect Tesla account")
                    }
                } footer: {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Version \(appVersion)")
                        Text("This app is read-only and does not control your vehicle.")
                        Text("This app is not affiliated with Tesla, Inc.")
                    }
                    .font(.caption2)
                }
            }
            .navigationTitle("Settings")
            .confirmationDialog("Delete all trip history?",
                                isPresented: $showDeleteConfirm, titleVisibility: .visible) {
                Button("Delete everything", role: .destructive) { /* calls DELETE /api/privacy/delete-all */ }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This permanently removes all stored trips, routes, and location points.")
            }
            .sheet(isPresented: $showExportSheet) {
                ExportPlaceholderView()
            }
            .task {
                zones = (try? await env.api.privacyZones()) ?? []
            }
        }
    }
}

struct AddPrivacyZonePlaceholder: View {
    var body: some View {
        ContentUnavailableView(
            "Add a privacy zone",
            systemImage: "lock.shield",
            description: Text("Pick a location and radius to hide exact positions (e.g. home)."))
            .navigationTitle("Privacy zone")
    }
}

struct ExportPlaceholderView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "doc.text").font(.largeTitle).foregroundStyle(.tint)
            Text("Your trip history will be exported as a CSV file.")
                .multilineTextAlignment(.center)
            Text("In the live build this downloads from /api/privacy/export.")
                .font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
        }
        .padding()
        .presentationDetents([.medium])
    }
}
