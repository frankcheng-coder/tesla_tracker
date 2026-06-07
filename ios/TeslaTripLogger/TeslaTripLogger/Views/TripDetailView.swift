import SwiftUI
import MapKit

struct TripDetailView: View {
    @EnvironmentObject var env: AppEnvironment
    let trip: Trip

    @State private var route: [CLLocationCoordinate2D] = []
    @State private var parkingAfter: ParkingEvent?

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                RouteMapView(route: routeForDisplay,
                             parking: parkingAfter.map { [$0] } ?? [])
                    .frame(height: 280)
                    .clipShape(RoundedRectangle(cornerRadius: 16))

                HStack {
                    Label(trip.startLabel, systemImage: "flag.fill").foregroundStyle(.green)
                    Spacer()
                    Image(systemName: "arrow.right").foregroundStyle(.secondary)
                    Spacer()
                    Label(trip.endLabel, systemImage: "flag.checkered").foregroundStyle(.red)
                }
                .font(.subheadline.weight(.medium))

                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                    StatCard(title: "Distance", value: Format.distance(trip.distanceMiles), icon: "ruler")
                    StatCard(title: "Duration", value: Format.duration(trip.durationSeconds), icon: "clock")
                    StatCard(title: "Avg speed", value: Format.speed(trip.avgSpeedMph), icon: "speedometer")
                    StatCard(title: "Max speed", value: Format.speed(trip.maxSpeedMph), icon: "gauge.high")
                    if let delta = trip.batteryDelta {
                        StatCard(title: "Battery",
                                 value: String(format: "%@ → %@ (%+.0f%%)",
                                               Format.battery(trip.startBatteryPercent),
                                               Format.battery(trip.endBatteryPercent), delta),
                                 icon: "battery.75")
                    }
                    if let so = trip.startOdometerMiles, let eo = trip.endOdometerMiles {
                        StatCard(title: "Odometer",
                                 value: String(format: "%.0f → %.0f mi", so, eo),
                                 icon: "car")
                    }
                }

                if let parking = parkingAfter {
                    parkingCard(parking)
                }

                Text("This app is read-only and does not control your vehicle.")
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                    .frame(maxWidth: .infinity)
                    .padding(.top, 8)
            }
            .padding()
        }
        .navigationTitle(Format.time(trip.startTime))
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private var routeForDisplay: [CLLocationCoordinate2D] {
        route.isEmpty ? [trip.startCoordinate, trip.endCoordinate] : route
    }

    private func parkingCard(_ parking: ParkingEvent) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Label("Parked after arrival", systemImage: "parkingsign")
                .font(.headline)
            if let dur = parking.durationSeconds {
                Text("Parked for \(Format.duration(dur)) at \(parking.placeName ?? trip.endLabel).")
                    .font(.subheadline).foregroundStyle(.secondary)
            } else {
                Text("Currently parked at \(parking.placeName ?? trip.endLabel).")
                    .font(.subheadline).foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
    }

    private func load() async {
        do {
            let r = try await env.api.tripRoute(tripId: trip.id)
            if let poly = r.routePolyline, !poly.isEmpty {
                route = Polyline.decode(poly)
            } else if let geo = r.routeGeojson {
                route = GeoJSON.lineString(geo)
            }
        } catch { /* fall back to straight line */ }

        if let vehicle = env.selectedVehicle,
           let events = try? await env.api.parkingEvents(vehicleId: vehicle.id) {
            parkingAfter = events.first { abs($0.startedAt.timeIntervalSince(trip.endTime)) < 60 }
        }
    }
}

struct StatCard: View {
    let title: String
    let value: String
    let icon: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Label(title, systemImage: icon)
                .font(.caption).foregroundStyle(.secondary)
            Text(value).font(.headline).minimumScaleFactor(0.7).lineLimit(1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
    }
}

/// Minimal GeoJSON LineString reader (coordinates are [lon, lat]).
enum GeoJSON {
    static func lineString(_ json: String) -> [CLLocationCoordinate2D] {
        guard let data = json.data(using: .utf8),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let coords = obj["coordinates"] as? [[Double]] else { return [] }
        return coords.compactMap { pair in
            pair.count == 2 ? CLLocationCoordinate2D(latitude: pair[1], longitude: pair[0]) : nil
        }
    }
}
