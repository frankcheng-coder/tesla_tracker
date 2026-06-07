import Foundation

enum Format {
    static let dayHeader: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "EEEE, MMMM d, yyyy"
        return f
    }()

    static let dateKey: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        return f
    }()

    static let clock: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "h:mm a"
        return f
    }()

    static func time(_ date: Date) -> String { clock.string(from: date) }
    static func day(_ date: Date) -> String { dayHeader.string(from: date) }
    static func dateKey(_ date: Date) -> String { dateKey.string(from: date) }

    static func distance(_ miles: Double) -> String {
        String(format: "%.1f mi", miles)
    }

    static func duration(_ seconds: Int) -> String {
        let m = seconds / 60
        if m < 60 { return "\(m) min" }
        let h = m / 60
        let rem = m % 60
        return rem == 0 ? "\(h) hr" : "\(h) hr \(rem) min"
    }

    static func speed(_ mph: Double?) -> String {
        guard let mph else { return "—" }
        return String(format: "%.0f mph", mph)
    }

    static func battery(_ pct: Double?) -> String {
        guard let pct else { return "—" }
        return String(format: "%.0f%%", pct)
    }
}
