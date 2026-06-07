import SwiftUI
import MapKit

/// Renders a route polyline with start/end markers, plus optional parking pins.
struct RouteMapView: View {
    let route: [CLLocationCoordinate2D]
    var parking: [ParkingEvent] = []
    var interactive: Bool = true

    private var region: MKCoordinateRegion {
        MapHelpers.region(covering: route + parking.map(\.coordinate))
    }

    var body: some View {
        Map(initialPosition: .region(region), interactionModes: interactive ? .all : []) {
            if route.count >= 2 {
                MapPolyline(coordinates: route)
                    .stroke(.tint, style: StrokeStyle(lineWidth: 5, lineCap: .round, lineJoin: .round))
            }
            if let start = route.first {
                Marker("Start", systemImage: "flag.fill", coordinate: start)
                    .tint(.green)
            }
            if let end = route.last {
                Marker("End", systemImage: "flag.checkered", coordinate: end)
                    .tint(.red)
            }
            ForEach(parking) { p in
                Marker(p.placeName ?? "Parked", systemImage: "parkingsign", coordinate: p.coordinate)
                    .tint(.blue)
            }
        }
    }
}

enum MapHelpers {
    static func region(covering coords: [CLLocationCoordinate2D]) -> MKCoordinateRegion {
        guard let first = coords.first else {
            return MKCoordinateRegion(
                center: .init(latitude: 37.3349, longitude: -122.0090),
                span: .init(latitudeDelta: 0.2, longitudeDelta: 0.2))
        }
        var minLat = first.latitude, maxLat = first.latitude
        var minLon = first.longitude, maxLon = first.longitude
        for c in coords {
            minLat = min(minLat, c.latitude); maxLat = max(maxLat, c.latitude)
            minLon = min(minLon, c.longitude); maxLon = max(maxLon, c.longitude)
        }
        let center = CLLocationCoordinate2D(
            latitude: (minLat + maxLat) / 2, longitude: (minLon + maxLon) / 2)
        let span = MKCoordinateSpan(
            latitudeDelta: max((maxLat - minLat) * 1.4, 0.01),
            longitudeDelta: max((maxLon - minLon) * 1.4, 0.01))
        return MKCoordinateRegion(center: center, span: span)
    }
}
