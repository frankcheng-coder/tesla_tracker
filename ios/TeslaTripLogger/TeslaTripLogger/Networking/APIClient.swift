import Foundation

protocol TripAPI {
    func vehicles() async throws -> [Vehicle]
    func trips(vehicleId: String, from: Date?, to: Date?) async throws -> [Trip]
    func tripRoute(tripId: String) async throws -> TripRoute
    func mapHistory(vehicleId: String, date: Date) async throws -> MapHistory
    func parkingEvents(vehicleId: String) async throws -> [ParkingEvent]
    func authStartURL() async throws -> URL
    func privacyZones() async throws -> [PrivacyZone]
}

enum APIError: Error { case badURL, badResponse(Int), decoding(Error) }

/// Live HTTP client talking to the FastAPI backend.
final class LiveAPIClient: TripAPI {
    private let baseURL: URL
    private let session: URLSession
    private let decoder: JSONDecoder

    init(baseURL: URL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
        let d = JSONDecoder()
        d.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let str = try container.decode(String.self)
            if let date = DateParsing.parse(str) { return date }
            throw DecodingError.dataCorruptedError(
                in: container, debugDescription: "Bad date: \(str)")
        }
        self.decoder = d
    }

    private func get<T: Decodable>(_ path: String, query: [URLQueryItem] = []) async throws -> T {
        guard var comps = URLComponents(
            url: baseURL.appendingPathComponent(path), resolvingAgainstBaseURL: false)
        else { throw APIError.badURL }
        if !query.isEmpty { comps.queryItems = query }
        guard let url = comps.url else { throw APIError.badURL }

        let (data, response) = try await session.data(from: url)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw APIError.badResponse((response as? HTTPURLResponse)?.statusCode ?? -1)
        }
        do { return try decoder.decode(T.self, from: data) }
        catch { throw APIError.decoding(error) }
    }

    func vehicles() async throws -> [Vehicle] {
        try await get("/api/vehicles")
    }

    func trips(vehicleId: String, from: Date?, to: Date?) async throws -> [Trip] {
        var q: [URLQueryItem] = []
        if let from { q.append(.init(name: "from", value: Format.dateKey(from))) }
        if let to { q.append(.init(name: "to", value: Format.dateKey(to))) }
        return try await get("/api/vehicles/\(vehicleId)/trips", query: q)
    }

    func tripRoute(tripId: String) async throws -> TripRoute {
        try await get("/api/trips/\(tripId)/route")
    }

    func mapHistory(vehicleId: String, date: Date) async throws -> MapHistory {
        try await get(
            "/api/vehicles/\(vehicleId)/map-history",
            query: [.init(name: "date", value: Format.dateKey(date))])
    }

    func parkingEvents(vehicleId: String) async throws -> [ParkingEvent] {
        try await get("/api/vehicles/\(vehicleId)/parking-events")
    }

    func authStartURL() async throws -> URL {
        struct Start: Decodable { let authorize_url: String }
        let start: Start = try await get("/auth/tesla/start")
        guard let url = URL(string: start.authorize_url) else { throw APIError.badURL }
        return url
    }

    func privacyZones() async throws -> [PrivacyZone] {
        try await get("/api/privacy/zones")
    }
}

/// Parses the ISO-8601 timestamps emitted by Python's `datetime.isoformat()`,
/// which may or may not include fractional seconds.
enum DateParsing {
    private static let withFraction: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()
    private static let plain: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()

    static func parse(_ str: String) -> Date? {
        withFraction.date(from: str) ?? plain.date(from: str)
    }
}
