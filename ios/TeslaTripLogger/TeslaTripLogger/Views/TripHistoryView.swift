import SwiftUI
import MapKit

struct TripHistoryView: View {
    @EnvironmentObject var env: AppEnvironment
    @State private var trips: [Trip] = []
    @State private var isLoading = false
    @State private var errorText: String?

    private var grouped: [(day: Date, trips: [Trip])] {
        let cal = Calendar.current
        let groups = Dictionary(grouping: trips) { cal.startOfDay(for: $0.startTime) }
        return groups.keys.sorted(by: >).map { ($0, groups[$0]!.sorted { $0.startTime < $1.startTime }) }
    }

    var body: some View {
        NavigationStack {
            Group {
                if isLoading && trips.isEmpty {
                    ProgressView("Loading trips…")
                } else if trips.isEmpty {
                    ContentUnavailableView(
                        "No trips yet",
                        systemImage: "car",
                        description: Text("History starts from the day you connect your vehicle."))
                } else {
                    List {
                        ForEach(grouped, id: \.day) { group in
                            Section(Format.day(group.day)) {
                                ForEach(group.trips) { trip in
                                    NavigationLink(value: trip) {
                                        TripRow(trip: trip)
                                    }
                                }
                            }
                        }
                    }
                    .listStyle(.insetGrouped)
                }
            }
            .navigationTitle("Trips")
            .navigationDestination(for: Trip.self) { TripDetailView(trip: $0) }
            .task { await load() }
            .refreshable { await load() }
        }
    }

    private func load() async {
        guard let vehicle = env.selectedVehicle else { return }
        isLoading = true
        defer { isLoading = false }
        do {
            trips = try await env.api.trips(vehicleId: vehicle.id, from: nil, to: nil)
        } catch {
            errorText = error.localizedDescription
        }
    }
}

struct TripRow: View {
    let trip: Trip

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(Format.time(trip.startTime))
                Image(systemName: "arrow.right").font(.caption2).foregroundStyle(.secondary)
                Text(Format.time(trip.endTime))
                Spacer()
            }
            .font(.subheadline.weight(.semibold))

            HStack(spacing: 6) {
                Text(trip.startLabel)
                Image(systemName: "arrow.right").font(.caption2).foregroundStyle(.secondary)
                Text(trip.endLabel)
            }
            .font(.body)
            .lineLimit(1)

            Text("\(Format.distance(trip.distanceMiles)) · \(Format.duration(trip.durationSeconds))")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, 4)
    }
}
