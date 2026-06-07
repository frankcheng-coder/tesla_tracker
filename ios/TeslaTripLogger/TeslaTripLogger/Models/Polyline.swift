import Foundation
import CoreLocation

/// Decoder for Google-format encoded polylines (matches the backend's
/// `polyline.encode`, precision 5). Used to draw trip routes on the map.
enum Polyline {
    static func decode(_ encoded: String) -> [CLLocationCoordinate2D] {
        var coordinates: [CLLocationCoordinate2D] = []
        var index = encoded.startIndex
        let end = encoded.endIndex
        var lat = 0
        var lon = 0

        while index < end {
            var result = 1
            var shift = 0
            var b: Int
            repeat {
                b = Int(encoded[index].asciiValue! - 63 - 1)
                index = encoded.index(after: index)
                result += b << shift
                shift += 5
            } while b >= 0x1f && index < end
            lat += (result & 1) != 0 ? -(result >> 1) : (result >> 1)

            result = 1
            shift = 0
            repeat {
                b = Int(encoded[index].asciiValue! - 63 - 1)
                index = encoded.index(after: index)
                result += b << shift
                shift += 5
            } while b >= 0x1f && index < end
            lon += (result & 1) != 0 ? -(result >> 1) : (result >> 1)

            coordinates.append(
                CLLocationCoordinate2D(
                    latitude: Double(lat) * 1e-5,
                    longitude: Double(lon) * 1e-5
                )
            )
        }
        return coordinates
    }
}
