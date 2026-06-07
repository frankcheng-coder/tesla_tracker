import Foundation
import CoreLocation

/// Local mock implementation so the UI runs in the simulator with no backend.
/// Mirrors the six canonical trips from the development plan.
final class MockAPIClient: TripAPI {
    static let vehicleId = "veh_mock_0001"

    private let places: [String: CLLocationCoordinate2D] = [
        "Home": .init(latitude: 37.3318, longitude: -122.0312),
        "Preschool": .init(latitude: 37.3505, longitude: -122.0250),
        "Costco": .init(latitude: 37.3760, longitude: -121.9750),
        "Work": .init(latitude: 37.3947, longitude: -122.1500),
        "Gym": .init(latitude: 37.3600, longitude: -122.0800),
    ]

    private lazy var day: Date = {
        var c = DateComponents()
        c.year = 2026; c.month = 6; c.day = 6
        c.timeZone = TimeZone(identifier: "UTC")
        return Calendar(identifier: .gregorian).date(from: c)!
    }()

    private struct Leg {
        let from: String, to: String
        let startMin: Int, durMin: Int
        let b0: Double, b1: Double
    }

    private let legs: [Leg] = [
        .init(from: "Home", to: "Preschool", startMin: 8 * 60 + 30, durMin: 25, b0: 82, b1: 80),
        .init(from: "Preschool", to: "Costco", startMin: 9 * 60 + 10, durMin: 18, b0: 80, b1: 78),
        .init(from: "Costco", to: "Home", startMin: 10 * 60 + 12, durMin: 23, b0: 78, b1: 75),
        .init(from: "Home", to: "Work", startMin: 13 * 60, durMin: 35, b0: 90, b1: 84),
        .init(from: "Work", to: "Gym", startMin: 17 * 60 + 30, durMin: 20, b0: 84, b1: 80),
        .init(from: "Gym", to: "Home", startMin: 18 * 60 + 45, durMin: 22, b0: 80, b1: 77),
    ]

    private func interp(_ a: CLLocationCoordinate2D, _ b: CLLocationCoordinate2D, n: Int = 8) -> [CLLocationCoordinate2D] {
        (0..<n).map { i in
            let f = Double(i) / Double(n - 1)
            return .init(latitude: a.latitude + (b.latitude - a.latitude) * f,
                         longitude: a.longitude + (b.longitude - a.longitude) * f)
        }
    }

    private func miles(_ pts: [CLLocationCoordinate2D]) -> Double {
        guard pts.count > 1 else { return 0 }
        var total = 0.0
        for i in 0..<(pts.count - 1) {
            let l1 = CLLocation(latitude: pts[i].latitude, longitude: pts[i].longitude)
            let l2 = CLLocation(latitude: pts[i + 1].latitude, longitude: pts[i + 1].longitude)
            total += l1.distance(from: l2)
        }
        return total / 1609.344
    }

    private lazy var cachedTrips: [Trip] = {
        legs.enumerated().map { idx, leg in
            let a = places[leg.from]!, b = places[leg.to]!
            let start = day.addingTimeInterval(Double(leg.startMin) * 60)
            let end = start.addingTimeInterval(Double(leg.durMin) * 60)
            let pts = interp(a, b)
            let dist = (miles(pts) * 100).rounded() / 100
            let avg = leg.durMin > 0 ? (dist / (Double(leg.durMin) / 60.0)) : 0
            return Trip(
                id: String(format: "trip_mock_%04d", idx + 1),
                vehicleId: Self.vehicleId,
                startTime: start, endTime: end,
                startLatitude: a.latitude, startLongitude: a.longitude,
                endLatitude: b.latitude, endLongitude: b.longitude,
                startPlaceName: leg.from, endPlaceName: leg.to,
                startOdometerMiles: 12000 + Double(idx) * 10,
                endOdometerMiles: 12000 + Double(idx) * 10 + dist,
                distanceMiles: dist,
                durationSeconds: leg.durMin * 60,
                avgSpeedMph: (avg * 10).rounded() / 10,
                maxSpeedMph: (avg * 16).rounded() / 10,
                startBatteryPercent: leg.b0, endBatteryPercent: leg.b1)
        }
    }()

    func vehicles() async throws -> [Vehicle] {
        [Vehicle(id: Self.vehicleId, vin: "5YJ3E1EA7PF000000",
                 displayName: "My Tesla", teslaVehicleId: "1000000000000001",
                 trackingEnabled: true, trackingPaused: false)]
    }

    func trips(vehicleId: String, from: Date?, to: Date?) async throws -> [Trip] {
        cachedTrips.filter { t in
            (from.map { t.startTime >= Calendar.current.startOfDay(for: $0) } ?? true) &&
            (to.map { t.startTime <= Calendar.current.startOfDay(for: $0).addingTimeInterval(86400) } ?? true)
        }
    }

    func tripRoute(tripId: String) async throws -> TripRoute {
        guard let trip = cachedTrips.first(where: { $0.id == tripId }) else {
            throw APIError.badResponse(404)
        }
        let pts = interp(trip.startCoordinate, trip.endCoordinate)
        let geojson = "{\"type\":\"LineString\",\"coordinates\":[" +
            pts.map { "[\($0.longitude),\($0.latitude)]" }.joined(separator: ",") + "]}"
        return TripRoute(tripId: tripId, routePolyline: nil, routeGeojson: geojson)
    }

    func mapHistory(vehicleId: String, date: Date) async throws -> MapHistory {
        let key = Format.dateKey(date)
        let trips = cachedTrips.filter { Format.dateKey($0.startTime) == key }
        let parking = try await parkingEvents(vehicleId: vehicleId)
            .filter { Format.dateKey($0.startedAt) == key }
        var timeline: [TimelineEntry] = []
        for t in trips {
            timeline.append(.init(time: t.startTime, event: "Left \(t.startLabel)"))
            timeline.append(.init(time: t.endTime, event: "Arrived at \(t.endLabel)"))
        }
        timeline.sort { $0.time < $1.time }
        return MapHistory(date: key, trips: trips, parkingEvents: parking, timeline: timeline)
    }

    func parkingEvents(vehicleId: String) async throws -> [ParkingEvent] {
        cachedTrips.enumerated().map { idx, t in
            let next = idx + 1 < cachedTrips.count ? cachedTrips[idx + 1] : nil
            let dur = next.map { Int($0.startTime.timeIntervalSince(t.endTime)) }
            return ParkingEvent(
                id: String(format: "park_mock_%04d", idx + 1),
                vehicleId: Self.vehicleId,
                startedAt: t.endTime, endedAt: next?.startTime,
                latitude: t.endLatitude, longitude: t.endLongitude,
                placeName: t.endPlaceName, durationSeconds: dur)
        }
    }

    func authStartURL() async throws -> URL {
        URL(string: "https://auth.tesla.com/oauth2/v3/authorize?mock=1")!
    }

    func privacyZones() async throws -> [PrivacyZone] { [] }
}
