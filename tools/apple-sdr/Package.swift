// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "apple-sdr",
    platforms: [.macOS(.v15)],
    targets: [
        .executableTarget(
            name: "apple-sdr",
            path: "Sources/apple-sdr",
            swiftSettings: [.swiftLanguageMode(.v5)]
        )
    ]
)
