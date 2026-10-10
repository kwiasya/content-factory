// vision-score: score sampled video frames with Apple's Vision framework.
// Usage: vision-score <video> [--fps 1] [--json out.json] [--max-side 1024] [--landmarks] [--faces-only]

import AVFoundation
import CoreGraphics
import Foundation
import Vision

// MARK: - Arguments

struct Options {
    var input: URL
    var fps: Double = 1
    var jsonOut: URL?
    var maxSide: Int = 1024
    var landmarks = false
    var facesOnly = false
}

func usage() -> Never {
    FileHandle.standardError.write(Data("""
    usage: vision-score <video> [--fps N] [--json out.json] [--max-side PX]
      --fps N        frames sampled per second (default 1)
      --json PATH    write the JSON array to PATH instead of stdout
      --max-side PX  downscale frames so the longer side is at most PX (default 1024, 0 = native)
      --landmarks    face landmarks; adds mouth_open (inner-lip gap / face height, largest face)
      --faces-only   skip aesthetics and humans (faster; those fields are null)

    """.utf8))
    exit(2)
}

func parseOptions() -> Options {
    var args = Array(CommandLine.arguments.dropFirst())
    var input: String?
    var opts = Options(input: URL(fileURLWithPath: "/"))
    while !args.isEmpty {
        let a = args.removeFirst()
        switch a {
        case "--fps":
            guard let v = args.first.flatMap(Double.init), v > 0 else { usage() }
            opts.fps = v; args.removeFirst()
        case "--json":
            guard let v = args.first else { usage() }
            opts.jsonOut = URL(fileURLWithPath: v); args.removeFirst()
        case "--max-side":
            guard let v = args.first.flatMap(Int.init), v >= 0 else { usage() }
            opts.maxSide = v; args.removeFirst()
        case "--landmarks":
            opts.landmarks = true
        case "--faces-only":
            opts.facesOnly = true
        case "-h", "--help":
            usage()
        default:
            if a.hasPrefix("-") || input != nil { usage() }
            input = a
        }
    }
    guard let input else { usage() }
    opts.input = URL(fileURLWithPath: input)
    return opts
}

// MARK: - Output

struct FrameScore {
    var t: Double
    var aesthetic: Float?
    var isUtility: Bool?
    var faces: Int?
    var maxFaceH: Double?
    var humans: Int?
    var maxHumanH: Double?
    var mouthOpen: Double?
    var landmarks = false
    var errors: [String] = []

    var json: String {
        func num(_ v: Double?) -> String { v.map { String(format: "%.4f", $0) } ?? "null" }
        func int(_ v: Int?) -> String { v.map(String.init) ?? "null" }
        var s = "{\"t\": \(String(format: "%.3f", t)), \"aesthetic\": \(num(aesthetic.map(Double.init)))"
        s += ", \"is_utility\": \(isUtility.map { $0 ? "true" : "false" } ?? "null")"
        s += ", \"faces\": \(int(faces)), \"max_face_h\": \(num(maxFaceH))"
        s += ", \"humans\": \(int(humans)), \"max_human_h\": \(num(maxHumanH))"
        if landmarks { s += ", \"mouth_open\": \(num(mouthOpen))" }
        if !errors.isEmpty {
            let escaped = errors.joined(separator: "; ")
                .replacingOccurrences(of: "\\", with: "\\\\")
                .replacingOccurrences(of: "\"", with: "\\\"")
                .replacingOccurrences(of: "\n", with: " ")
            s += ", \"error\": \"\(escaped)\""
        }
        return s + "}"
    }
}

/// Short one-line error text (NSError descriptions are multi-line and very long).
func brief(_ error: Error) -> String {
    let e = error as NSError
    return "\(e.localizedDescription) (\(e.domain) \(e.code))"
}

func log(_ msg: String) {
    FileHandle.standardError.write(Data((msg + "\n").utf8))
}

// MARK: - Scoring

let aestheticsRequest = CalculateImageAestheticsScoresRequest()
let faceRequest = DetectFaceRectanglesRequest()
let landmarksRequest = DetectFaceLandmarksRequest()

/// Inner-lip vertical extent over face-box height, both in image pixels; nil without inner-lip points.
func mouthOpen(_ face: FaceObservation, size: CGSize) -> Double? {
    guard let lips = face.landmarks?.innerLips else { return nil }
    let ys = lips.pointsInImageCoordinates(size).map { Double($0.y) }
    let faceH = Double(face.boundingBox.height) * Double(size.height)
    guard let lo = ys.min(), let hi = ys.max(), faceH > 0 else { return nil }
    return (hi - lo) / faceH
}

func score(_ image: CGImage, at t: Double, humanReq: DetectHumanRectanglesRequest) async -> FrameScore {
    var out = FrameScore(t: t)
    out.landmarks = opts.landmarks
    // One handler per frame so Vision can share the decoded image across requests.
    let handler = ImageRequestHandler(image)

    if !opts.facesOnly {
        do {
            let obs = try await handler.perform(aestheticsRequest)
            out.aesthetic = obs.overallScore
            out.isUtility = obs.isUtility
        } catch {
            out.errors.append("aesthetics: \(brief(error))")
        }
    }

    do {
        let faces = opts.landmarks ? try await handler.perform(landmarksRequest) : try await handler.perform(faceRequest)
        out.faces = faces.count
        out.maxFaceH = faces.map { Double($0.boundingBox.height) }.max() ?? 0
        if opts.landmarks, let big = faces.max(by: { $0.boundingBox.height < $1.boundingBox.height }) {
            out.mouthOpen = mouthOpen(big, size: CGSize(width: image.width, height: image.height))
        }
    } catch {
        out.errors.append("faces: \(brief(error))")
    }

    if opts.facesOnly { return out }
    do {
        let humans = try await handler.perform(humanReq)
        out.humans = humans.count
        out.maxHumanH = humans.map { Double($0.boundingBox.height) }.max() ?? 0
    } catch {
        out.errors.append("humans: \(brief(error))")
    }

    return out
}

// MARK: - Main

let opts = parseOptions()
let started = Date()

guard FileManager.default.fileExists(atPath: opts.input.path) else {
    log("vision-score: no such file: \(opts.input.path)")
    exit(1)
}

let asset = AVURLAsset(url: opts.input)
let duration: Double
do {
    duration = try await asset.load(.duration).seconds
    guard duration.isFinite, duration > 0 else { throw CocoaError(.fileReadCorruptFile) }
    guard try await !asset.loadTracks(withMediaType: .video).isEmpty else {
        log("vision-score: no video track in \(opts.input.path)")
        exit(1)
    }
} catch {
    log("vision-score: cannot read \(opts.input.path): \(error)")
    exit(1)
}

let generator = AVAssetImageGenerator(asset: asset)
generator.appliesPreferredTrackTransform = true   // honour rotation metadata
if opts.maxSide > 0 {
    generator.maximumSize = CGSize(width: opts.maxSide, height: opts.maxSide) // aspect preserved
}
let step = 1.0 / opts.fps
let tolerance = CMTime(seconds: min(0.05, step / 4), preferredTimescale: 600)
generator.requestedTimeToleranceBefore = tolerance
generator.requestedTimeToleranceAfter = tolerance

var humanReq = DetectHumanRectanglesRequest()
humanReq.upperBodyOnly = false

var results: [String] = []
var aestheticSum = 0.0
var aestheticCount = 0
var frameMs: [Double] = []   // decode + Vision, per frame
var visionMs: [Double] = []  // Vision only, per frame

var i = 0
while true {
    let t = Double(i) * step
    if t >= duration { break }
    i += 1
    let frameStart = Date()
    let image: CGImage
    let actual: Double
    do {
        let r = try await generator.image(at: CMTime(seconds: t, preferredTimescale: 600))
        image = r.image
        actual = r.actualTime.seconds
    } catch {
        log("vision-score: t=\(String(format: "%.3f", t)) frame decode failed: \(brief(error))")
        continue
    }
    let visionStart = Date()
    let s = await score(image, at: actual.isFinite ? actual : t, humanReq: humanReq)
    visionMs.append(Date().timeIntervalSince(visionStart) * 1000)
    if let a = s.aesthetic { aestheticSum += Double(a); aestheticCount += 1 }
    if !s.errors.isEmpty { log("vision-score: t=\(String(format: "%.3f", s.t)) \(s.errors.joined(separator: "; "))") }
    results.append(s.json)
    frameMs.append(Date().timeIntervalSince(frameStart) * 1000)
}

let body = "[\n" + results.map { "  " + $0 }.joined(separator: ",\n") + (results.isEmpty ? "]\n" : "\n]\n")
if let path = opts.jsonOut {
    do { try body.write(to: path, atomically: true, encoding: .utf8) }
    catch { log("vision-score: cannot write \(path.path): \(error)"); exit(1) }
} else {
    FileHandle.standardOutput.write(Data(body.utf8))
}

let elapsed = Date().timeIntervalSince(started)
let mean = aestheticCount > 0 ? aestheticSum / Double(aestheticCount) : .nan
func avg(_ xs: ArraySlice<Double>) -> Double { xs.isEmpty ? 0 : xs.reduce(0, +) / Double(xs.count) }
// First frame includes one-off Vision model load; report it separately from the steady state.
let warm = frameMs.first ?? 0
let steady = avg(frameMs.dropFirst())
let steadyVision = avg(visionMs.dropFirst())
log(String(format: "vision-score: %d frames scored, mean aesthetic %.3f, %.2fs elapsed (first frame %.0f ms, then %.0f ms/frame, %.0f ms in Vision)",
           results.count, mean, elapsed, warm, steady, steadyVision))
exit(results.isEmpty ? 1 : 0)
