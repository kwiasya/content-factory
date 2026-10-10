// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "vision-score",
    platforms: [.macOS(.v15)],
    targets: [
        .executableTarget(
            name: "vision-score",
            path: "Sources/vision-score"
        )
    ]
)
