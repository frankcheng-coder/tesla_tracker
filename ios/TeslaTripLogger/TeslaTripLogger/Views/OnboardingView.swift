import SwiftUI

struct OnboardingView: View {
    @EnvironmentObject var env: AppEnvironment

    var body: some View {
        VStack(spacing: 28) {
            Spacer()

            Image(systemName: "car.side.and.exclamationmark")
                .font(.system(size: 64))
                .foregroundStyle(.tint)
                .symbolRenderingMode(.hierarchical)
                .accessibilityHidden(true)

            VStack(spacing: 10) {
                Text("Tesla Trips")
                    .font(.largeTitle.bold())
                Text("See where your Tesla went.")
                    .font(.title3)
                    .foregroundStyle(.secondary)
            }

            VStack(alignment: .leading, spacing: 16) {
                FeatureRow(icon: "map", title: "Private trip history",
                           detail: "Routes, parking, mileage — all yours.")
                FeatureRow(icon: "lock.shield", title: "Read-only",
                           detail: "This app never controls your vehicle.")
                FeatureRow(icon: "calendar.badge.clock", title: "Starts today",
                           detail: "History starts from the day you connect your vehicle.")
            }
            .padding(.horizontal)

            Spacer()

            Button {
                Task {
                    // In the live build this opens the Tesla OAuth URL in a
                    // web auth session. In mock mode we connect immediately.
                    _ = try? await env.api.authStartURL()
                    env.markConnected()
                    await env.loadVehicles()
                }
            } label: {
                Text("Connect Tesla")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 6)
            }
            .buttonStyle(.borderedProminent)
            .padding(.horizontal)

            Text("This app is not affiliated with Tesla, Inc.")
                .font(.caption2)
                .foregroundStyle(.tertiary)
                .padding(.bottom, 8)
        }
        .padding()
    }
}

struct FeatureRow: View {
    let icon: String
    let title: String
    let detail: String

    var body: some View {
        HStack(alignment: .top, spacing: 14) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundStyle(.tint)
                .frame(width: 32)
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.headline)
                Text(detail).font(.subheadline).foregroundStyle(.secondary)
            }
        }
    }
}

#Preview {
    OnboardingView().environmentObject(AppEnvironment())
}
