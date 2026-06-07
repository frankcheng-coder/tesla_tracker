import SwiftUI

struct VehicleSelectionView: View {
    @EnvironmentObject var env: AppEnvironment

    var body: some View {
        NavigationStack {
            List {
                Section {
                    ForEach(env.vehicles) { vehicle in
                        Button {
                            env.selectedVehicle = vehicle
                        } label: {
                            HStack {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(vehicle.name).font(.headline)
                                    Text("VIN \(vehicle.vin)")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                                Spacer()
                                if env.selectedVehicle?.id == vehicle.id {
                                    Image(systemName: "checkmark.circle.fill")
                                        .foregroundStyle(.tint)
                                }
                            }
                        }
                        .tint(.primary)
                    }
                } header: {
                    Text("Select a vehicle")
                } footer: {
                    Text("Read-only trip tracking will be enabled for the selected vehicle.")
                }

                if env.vehicles.isEmpty {
                    ContentUnavailableView(
                        "No vehicles found",
                        systemImage: "car",
                        description: Text("Make sure your Tesla account is connected."))
                }
            }
            .navigationTitle("Your Tesla")
            .task { await env.loadVehicles() }
        }
    }
}
