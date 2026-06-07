import SwiftUI
import MapKit

struct MapHistoryView: View {
    @EnvironmentObject var env: AppEnvironment
    @State private var date = Self.defaultDate
    @State private var history: MapHistory?
    @State private var isLoading = false

    // Default to the mock data's reference day so there's something to show.
    static var defaultDate: Date {
        DateParsing.parse("2026-06-06T12:00:00+00:00") ?? Date()
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                DatePicker("Date", selection: $date, displayedComponents: .date)
                    .datePickerStyle(.compact)
                    .padding(.horizontal)
                    .padding(.vertical, 8)
                    .onChange(of: date) { _, _ in Task { await load() } }

                if let history, !history.trips.isEmpty {
                    RouteMapView(route: allRoutePoints(history),
                                 parking: history.parkingEvents)
                        .frame(height: 300)

                    List {
                        Section("Timeline") {
                            ForEach(history.timeline) { entry in
                                HStack(alignment: .top, spacing: 12) {
                                    Text(Format.time(entry.time))
                                        .font(.subheadline.monospacedDigit().weight(.semibold))
                                        .frame(width: 78, alignment: .leading)
                                    Text(entry.event)
                                    Spacer()
                                }
                            }
                        }
                    }
                    .listStyle(.plain)
                } else {
                    Spacer()
                    if isLoading {
                        ProgressView()
                    } else {
                        ContentUnavailableView(
                            "No activity",
                            systemImage: "map",
                            description: Text("No trips recorded on this day."))
                    }
                    Spacer()
                }
            }
            .navigationTitle("Map History")
            .task { await load() }
        }
    }

    private func allRoutePoints(_ history: MapHistory) -> [CLLocationCoordinate2D] {
        history.trips.flatMap { [$0.startCoordinate, $0.endCoordinate] }
    }

    private func load() async {
        guard let vehicle = env.selectedVehicle else { return }
        isLoading = true
        defer { isLoading = false }
        history = try? await env.api.mapHistory(vehicleId: vehicle.id, date: date)
    }
}
