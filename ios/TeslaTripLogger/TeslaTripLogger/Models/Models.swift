import Foundation
import CoreLocation

// MARK: - API models (mirror the FastAPI backend schemas)

struct Vehicle: Codable, Identifiable, Hashable {
    let id: String
    let vin: String
    let displayName: String?
    let teslaVehicleId: String?
    let trackingEnabled: Bool
    let trackingPaused: Bool

    enum CodingKeys: String, CodingKey {
        case id, vin
        case displayName = "display_name"
        case teslaVehicleId = "tesla_vehicle_id"
        case trackingEnabled = "tracking_enabled"
        case trackingPaused = "tracking_paused"
    }

    var name: String { displayName ?? "My Tesla" }
}

struct Trip: Codable, Identifiable, Hashable {
    let id: String
    let vehicleId: String
    let startTime: Date
    let endTime: Date
    let startLatitude: Double
    let startLongitude: Double
    let endLatitude: Double
    let endLongitude: Double
    let startPlaceName: String?
    let endPlaceName: String?
    let startOdometerMiles: Double?
    let endOdometerMiles: Double?
    let distanceMiles: Double
    let durationSeconds: Int
    let avgSpeedMph: Double?
    let maxSpeedMph: Double?
    let startBatteryPercent: Double?
    let endBatteryPercent: Double?

    enum CodingKeys: String, CodingKey {
        case id
        case vehicleId = "vehicle_id"
        case startTime = "start_time"
        case endTime = "end_time"
        case startLatitude = "start_latitude"
        case startLongitude = "start_longitude"
        case endLatitude = "end_latitude"
        case endLongitude = "end_longitude"
        case startPlaceName = "start_place_name"
        case endPlaceName = "end_place_name"
        case startOdometerMiles = "start_odometer_miles"
        case endOdometerMiles = "end_odometer_miles"
        case distanceMiles = "distance_miles"
        case durationSeconds = "duration_seconds"
        case avgSpeedMph = "avg_speed_mph"
        case maxSpeedMph = "max_speed_mph"
        case startBatteryPercent = "start_battery_percent"
        case endBatteryPercent = "end_battery_percent"
    }

    var startCoordinate: CLLocationCoordinate2D {
        .init(latitude: startLatitude, longitude: startLongitude)
    }
    var endCoordinate: CLLocationCoordinate2D {
        .init(latitude: endLatitude, longitude: endLongitude)
    }
    var startLabel: String { startPlaceName ?? "Start" }
    var endLabel: String { endPlaceName ?? "End" }
    var batteryDelta: Double? {
        guard let s = startBatteryPercent, let e = endBatteryPercent else { return nil }
        return e - s
    }
}

struct TripRoute: Codable {
    let tripId: String
    let routePolyline: String?
    let routeGeojson: String?

    enum CodingKeys: String, CodingKey {
        case tripId = "trip_id"
        case routePolyline = "route_polyline"
        case routeGeojson = "route_geojson"
    }
}

struct ParkingEvent: Codable, Identifiable, Hashable {
    let id: String
    let vehicleId: String
    let startedAt: Date
    let endedAt: Date?
    let latitude: Double
    let longitude: Double
    let placeName: String?
    let durationSeconds: Int?

    enum CodingKeys: String, CodingKey {
        case id
        case vehicleId = "vehicle_id"
        case startedAt = "started_at"
        case endedAt = "ended_at"
        case latitude, longitude
        case placeName = "place_name"
        case durationSeconds = "duration_seconds"
    }

    var coordinate: CLLocationCoordinate2D { .init(latitude: latitude, longitude: longitude) }
}

struct TimelineEntry: Codable, Identifiable, Hashable {
    var id: String { "\(time.timeIntervalSince1970)-\(event)" }
    let time: Date
    let event: String
}

struct MapHistory: Codable {
    let date: String
    let trips: [Trip]
    let parkingEvents: [ParkingEvent]
    let timeline: [TimelineEntry]

    enum CodingKeys: String, CodingKey {
        case date, trips, timeline
        case parkingEvents = "parking_events"
    }
}

struct PrivacyZone: Codable, Identifiable, Hashable {
    let id: String
    let name: String
    let latitude: Double
    let longitude: Double
    let radiusMeters: Double
    let hideExactLocation: Bool

    enum CodingKeys: String, CodingKey {
        case id, name, latitude, longitude
        case radiusMeters = "radius_meters"
        case hideExactLocation = "hide_exact_location"
    }
}
