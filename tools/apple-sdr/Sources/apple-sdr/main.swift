// apple-sdr: an HDR clip (iPhone HLG / Dolby Vision 8.4) as an SDR Rec.709 mezzanine, tone-mapped
// by AVFoundation itself, so it looks as it does in QuickTime and Photos.
//
// Usage:
//   apple-sdr convert <in> <out.mov> [--method colorsync|vt709|vt2020|composition|export]
//                     [--start S] [--duration S]
//   apple-sdr frames <in> --at T[,T...] --out-dir DIR [--prefix NAME] [--policy sdr|source]
//                    [--space display-p3|srgb|709|native]
//
// convert: ProRes 422 HQ, Rec.709 tags (1-1-1), the source fps, size and orientation, every audio
//          track passed through unchanged. Written to <out>.partial.mov and renamed when complete.
// frames:  AVAssetImageGenerator stills at exact times (forceSDR: Apple's SDR rendition of an HDR
//          clip), drawn by ColorSync into --space (Display P3 by default, i.e. as on a Mac screen)
//          as 8-bit PNG; the reference for checks.
// One JSON object on stdout; progress and errors on stderr.

import AVFoundation
import CoreGraphics
import CoreImage
import CoreMedia
import CoreVideo
import Foundation
import ColorSync
import ImageIO
import UniformTypeIdentifiers

let version = "1"

func log(_ s: String) { FileHandle.standardError.write(Data((s + "\n").utf8)) }

func fail(_ s: String, code: Int32 = 1) -> Never {
    log("apple-sdr: " + s)
    exit(code)
}

func usage() -> Never {
    log("""
    usage: apple-sdr convert <in> <out.mov> [--method colorsync|vt709|vt2020|composition|export]
                             [--start S] [--duration S]
           apple-sdr frames <in> --at T[,T...] --out-dir DIR [--prefix NAME] [--policy sdr|source]
                            [--space display-p3|srgb|709|native]
      convert   SDR Rec.709 ProRes 422 HQ mezzanine via AVFoundation's HDR->SDR tone mapping
                (default method 'colorsync': forceSDR tone mapping, then BT.2020-SDR -> 709 as ColorSync does)
      frames    AVAssetImageGenerator stills as 8-bit PNG (policy sdr = forceSDR, default), converted by
                ColorSync to --space (display-p3 by default: as they look on a Mac screen)
    """)
    exit(2)
}

func emit(_ obj: [String: Any]) {
    let data = try! JSONSerialization.data(withJSONObject: obj, options: [.prettyPrinted, .sortedKeys])
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write(Data("\n".utf8))
}

let rec709: [String: Any] = [
    AVVideoColorPrimariesKey: AVVideoColorPrimaries_ITU_R_709_2,
    AVVideoTransferFunctionKey: AVVideoTransferFunction_ITU_R_709_2,
    AVVideoYCbCrMatrixKey: AVVideoYCbCrMatrix_ITU_R_709_2,
]

// BT.2020 primaries with the SDR (709) transfer: what AVAssetImageGenerator's forceSDR returns.
let sdr2020: [String: Any] = [
    AVVideoColorPrimariesKey: AVVideoColorPrimaries_ITU_R_2020,
    AVVideoTransferFunctionKey: AVVideoTransferFunction_ITU_R_709_2,
    AVVideoYCbCrMatrixKey: AVVideoYCbCrMatrix_ITU_R_2020,
]

// 10-bit 4:2:2 video range: what the ProRes 422 encoder takes natively, no 8-bit step.
let readerPixelFormat = kCVPixelFormatType_422YpCbCr10BiPlanarVideoRange

func fourCC(_ v: FourCharCode) -> String {
    let bytes = [24, 16, 8, 0].map { UInt8((v >> UInt32($0)) & 0xff) }
    return String(bytes: bytes, encoding: .ascii) ?? String(v)
}

func colorTags(_ fd: CMFormatDescription) -> [String: Any] {
    let ext = CMFormatDescriptionGetExtensions(fd) as? [String: Any] ?? [:]
    var out: [String: Any] = [:]
    for (k, name) in [(kCMFormatDescriptionExtension_ColorPrimaries, "primaries"),
                      (kCMFormatDescriptionExtension_TransferFunction, "transfer"),
                      (kCMFormatDescriptionExtension_YCbCrMatrix, "matrix")] {
        if let v = ext[k as String] { out[name] = "\(v)" }
    }
    return out
}

// MARK: - Arguments

var args = Array(CommandLine.arguments.dropFirst())
guard let command = args.first else { usage() }
args.removeFirst()

@MainActor
func takeValue(_ name: String) -> String? {
    guard let i = args.firstIndex(of: name) else { return nil }
    guard i + 1 < args.count else { usage() }
    let v = args[i + 1]
    args.removeSubrange(i...(i + 1))
    return v
}

// MARK: - convert

// colorsync (default): the reader decodes with the forceSDR tags (BT.2020 primaries, SDR 709
//   transfer), which gives AVAssetImageGenerator's forceSDR pixels exactly; Core Image then
//   converts BT.2020-SDR -> Rec.709 with the CoreMedia color spaces of both tag sets, i.e. the
//   ColorSync transform a Mac uses to show each of them. So the 709 file shows as the
//   forceSDR rendition does.
// vt709: the reader converts straight to Rec.709 (VideoToolbox's own gamut step; measured
//   +7 to +8 levels brighter on screen than forceSDR on IMG_0477). vt2020: the forceSDR-tagged
//   buffers written as they are (BT.2020 / 709 / BT.2020). composition, export: AVVideoComposition
//   in Rec.709 through a reader or an AVAssetExportSession (ProRes 422, LPCM); same pixels as vt709.
enum Method: String { case colorsync, vt709, vt2020, composition, export }

func attachments(_ props: [String: Any]) -> [String: Any] {
    let p = props[AVVideoColorPrimariesKey] as! String
    let t = props[AVVideoTransferFunctionKey] as! String
    let m = props[AVVideoYCbCrMatrixKey] as! String
    return [kCVImageBufferColorPrimariesKey as String: p, kCVImageBufferTransferFunctionKey as String: t,
            kCVImageBufferYCbCrMatrixKey as String: m]
}

@MainActor
func convert() async {
    let method = Method(rawValue: takeValue("--method") ?? "colorsync") ?? { usage() }()
    let start = takeValue("--start").map { Double($0) ?? { usage() }() }
    let duration = takeValue("--duration").map { Double($0) ?? { usage() }() }
    guard args.count == 2, !args.contains(where: { $0.hasPrefix("--") }) else { usage() }
    let input = URL(fileURLWithPath: args[0])
    let output = URL(fileURLWithPath: args[1])
    let partial = output.deletingPathExtension().appendingPathExtension("partial.mov")
    try? FileManager.default.removeItem(at: partial)
    let readProps = (method == .colorsync || method == .vt2020) ? sdr2020 : rec709
    let writeProps = method == .vt2020 ? sdr2020 : rec709

    let t0 = Date()
    let asset = AVURLAsset(url: input)
    let vtrack: AVAssetTrack
    let naturalSize: CGSize
    let transform: CGAffineTransform
    let nominalFps: Float
    let srcFormats: [CMFormatDescription]
    let assetDuration: CMTime
    let atracks: [AVAssetTrack]
    let metadata: [AVMetadataItem]
    do {
        guard let v = try await asset.loadTracks(withMediaType: .video).first else { fail("no video track in \(input.path)") }
        vtrack = v
        (naturalSize, transform, nominalFps, srcFormats) = try await v.load(
            .naturalSize, .preferredTransform, .nominalFrameRate, .formatDescriptions)
        assetDuration = try await asset.load(.duration)
        atracks = try await asset.loadTracks(withMediaType: .audio)
        metadata = (try? await asset.load(.metadata)) ?? []
    } catch {
        fail("cannot open \(input.path): \(error.localizedDescription)")
    }
    var range: CMTimeRange? = nil
    if start != nil || duration != nil {
        let s = CMTime(seconds: start ?? 0, preferredTimescale: 600)
        let d = duration.map { CMTime(seconds: $0, preferredTimescale: 600) } ?? (assetDuration - s)
        range = CMTimeRange(start: s, duration: d)
    }

    // A composition renders display-oriented frames in Rec.709 (rotation baked in).
    func composition709() async throws -> AVMutableVideoComposition {
        let comp = try await AVMutableVideoComposition.videoComposition(withPropertiesOf: asset)
        comp.colorPrimaries = AVVideoColorPrimaries_ITU_R_709_2
        comp.colorTransferFunction = AVVideoTransferFunction_ITU_R_709_2
        comp.colorYCbCrMatrix = AVVideoYCbCrMatrix_ITU_R_709_2
        return comp
    }

    var result: [String: Any] = [
        "tool": "apple-sdr", "version": version, "method": method.rawValue,
        "input": input.path, "output": output.path,
        "source": ["width": Int(naturalSize.width), "height": Int(naturalSize.height),
                   "nominal_fps": Double(nominalFps),
                   "transform": [transform.a, transform.b, transform.c, transform.d, transform.tx, transform.ty],
                   "color": srcFormats.first.map(colorTags) ?? [:],
                   "audio_tracks": atracks.count] as [String: Any],
    ]

    if method == .export {
        guard let ex = AVAssetExportSession(asset: asset, presetName: AVAssetExportPresetAppleProRes422LPCM) else {
            fail("no export session")
        }
        do {
            ex.videoComposition = try await composition709()
            if let range { ex.timeRange = range }
            try await ex.export(to: partial, as: .mov)
        } catch {
            fail("export failed: \(error.localizedDescription)")
        }
    } else {
        let reader: AVAssetReader
        let writer: AVAssetWriter
        do {
            reader = try AVAssetReader(asset: asset)
            writer = try AVAssetWriter(outputURL: partial, fileType: .mov)
        } catch {
            fail("cannot set up reader/writer: \(error.localizedDescription)")
        }
        if let range { reader.timeRange = range }
        // Coded size (the decoded buffers'); naturalSize can already be the rotated display size.
        let coded = srcFormats.first.map { CMVideoFormatDescriptionGetDimensions($0) }
        var outW = Int(coded?.width ?? Int32(naturalSize.width)), outH = Int(coded?.height ?? Int32(naturalSize.height))
        let vout: AVAssetReaderOutput
        if method == .composition {
            let o = AVAssetReaderVideoCompositionOutput(videoTracks: [vtrack], videoSettings: [
                kCVPixelBufferPixelFormatTypeKey as String: readerPixelFormat,
            ])
            do { o.videoComposition = try await composition709() } catch { fail("composition: \(error)") }
            outW = Int(o.videoComposition!.renderSize.width)
            outH = Int(o.videoComposition!.renderSize.height)
            vout = o
        } else {
            vout = AVAssetReaderTrackOutput(track: vtrack, outputSettings: [
                kCVPixelBufferPixelFormatTypeKey as String: readerPixelFormat,
                AVVideoColorPropertiesKey: readProps,
            ])
        }
        vout.alwaysCopiesSampleData = false
        guard reader.canAdd(vout) else { fail("reader cannot add the video output") }
        reader.add(vout)
        let vin = AVAssetWriterInput(mediaType: .video, outputSettings: [
            AVVideoCodecKey: AVVideoCodecType.proRes422HQ,
            AVVideoWidthKey: outW, AVVideoHeightKey: outH,
            AVVideoColorPropertiesKey: writeProps,
        ])
        vin.expectsMediaDataInRealTime = false
        if method != .composition { vin.transform = transform }
        guard writer.canAdd(vin) else { fail("writer cannot add the ProRes video input") }
        writer.add(vin)

        // colorsync: Core Image converts each frame into a pool buffer tagged Rec.709.
        var adaptor: AVAssetWriterInputPixelBufferAdaptor? = nil
        let ci = CIContext(options: [.cacheIntermediates: false, .workingFormat: CIFormat.RGBAh])
        let dstAttachments = attachments(rec709)
        let dstSpace = CVImageBufferCreateColorSpaceFromAttachments(dstAttachments as CFDictionary)!.takeRetainedValue()
        // The reader converts every frame into readProps, so those tags define the source space
        // (some decoders leave the attachments off the buffers).
        let srcSpace = CVImageBufferCreateColorSpaceFromAttachments(attachments(readProps) as CFDictionary)!
            .takeRetainedValue()
        if method == .colorsync {
            adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: vin, sourcePixelBufferAttributes: [
                kCVPixelBufferPixelFormatTypeKey as String: readerPixelFormat,
                kCVPixelBufferWidthKey as String: outW, kCVPixelBufferHeightKey as String: outH,
                kCVPixelBufferIOSurfacePropertiesKey as String: [:] as [String: Any],
            ])
            result["colorsync"] = ["read_as": attachments(readProps), "from_space": describe(srcSpace),
                                   "to": dstAttachments, "to_space": describe(dstSpace)]
        }

        var pairs: [(AVAssetReaderOutput, AVAssetWriterInput, String)] = [(vout, vin, "video")]
        var audioRows: [[String: Any]] = []
        for (i, at) in atracks.enumerated() {
            let fds = (try? await at.load(.formatDescriptions)) ?? []
            let sub = fds.first.map { fourCC(CMFormatDescriptionGetMediaSubType($0)) } ?? "?"
            let o = AVAssetReaderTrackOutput(track: at, outputSettings: nil)
            o.alwaysCopiesSampleData = false
            let wi = AVAssetWriterInput(mediaType: .audio, outputSettings: nil, sourceFormatHint: fds.first)
            wi.expectsMediaDataInRealTime = false
            if reader.canAdd(o) && writer.canAdd(wi) {
                reader.add(o)
                writer.add(wi)
                pairs.append((o, wi, "audio\(i)"))
                audioRows.append(["track": i, "codec": sub, "copied": true])
            } else {
                audioRows.append(["track": i, "codec": sub, "copied": false])
                log("apple-sdr: audio track \(i) (\(sub)) cannot be passed through; skipped")
            }
        }
        result["audio"] = audioRows
        writer.metadata = metadata.filter { $0.commonKey != nil || $0.identifier != nil }

        guard reader.startReading() else { fail("reader: \(reader.error?.localizedDescription ?? "?")") }
        guard writer.startWriting() else { fail("writer: \(writer.error?.localizedDescription ?? "?")") }
        writer.startSession(atSourceTime: range?.start ?? .zero)

        var done = Array(repeating: false, count: pairs.count)
        var frames = 0
        var firstAttachments: [String: Any] = [:]
        var lastReport = Date()
        while done.contains(false) {
            var progressed = false
            for (i, (out, inp, kind)) in pairs.enumerated() where !done[i] {
                guard inp.isReadyForMoreMediaData else { continue }
                progressed = true
                guard let sb = out.copyNextSampleBuffer() else {
                    if reader.status == .failed { fail("reader failed: \(reader.error?.localizedDescription ?? "?")") }
                    inp.markAsFinished()
                    done[i] = true
                    continue
                }
                if kind == "video", let pb = CMSampleBufferGetImageBuffer(sb) {
                    if frames == 0 {
                        for k in [kCVImageBufferColorPrimariesKey, kCVImageBufferTransferFunctionKey,
                                  kCVImageBufferYCbCrMatrixKey] {
                            if let v = CVBufferCopyAttachment(pb, k, nil) { firstAttachments[k as String] = "\(v)" }
                        }
                    }
                    frames += 1
                    if let adaptor {
                        guard let pool = adaptor.pixelBufferPool else { fail("no pixel buffer pool") }
                        var outPB: CVPixelBuffer?
                        CVPixelBufferPoolCreatePixelBuffer(nil, pool, &outPB)
                        guard let outPB else { fail("cannot allocate a pixel buffer") }
                        CVBufferSetAttachments(outPB, dstAttachments as CFDictionary, .shouldPropagate)
                        let img = CIImage(cvPixelBuffer: pb, options: [.colorSpace: srcSpace])
                        ci.render(img, to: outPB, bounds: img.extent, colorSpace: dstSpace)
                        if !adaptor.append(outPB, withPresentationTime: CMSampleBufferGetPresentationTimeStamp(sb)) {
                            fail("append video failed: \(writer.error?.localizedDescription ?? "?")")
                        }
                        continue
                    }
                }
                if !inp.append(sb) {
                    fail("append \(kind) failed: \(writer.error?.localizedDescription ?? "?")")
                }
            }
            if !progressed { usleep(2000) }
            if Date().timeIntervalSince(lastReport) > 5 {
                log("apple-sdr: \(frames) frames, \(String(format: "%.0f", Date().timeIntervalSince(t0))) s")
                lastReport = Date()
            }
        }
        await writer.finishWriting()
        if writer.status != .completed { fail("writer: \(writer.error?.localizedDescription ?? "status \(writer.status.rawValue)")") }
        result["frames"] = frames
        result["read_color"] = firstAttachments
        result["size"] = ["width": outW, "height": outH]
    }
    do {
        try? FileManager.default.removeItem(at: output)
        try FileManager.default.moveItem(at: partial, to: output)
    } catch {
        fail("cannot move \(partial.path) to \(output.path): \(error.localizedDescription)")
    }
    let secs = Date().timeIntervalSince(t0)
    result["seconds"] = (secs * 10).rounded() / 10
    log("apple-sdr: \(output.lastPathComponent) written in \(String(format: "%.1f", secs)) s")
    emit(result)
}

// MARK: - frames

func describe(_ cs: CGColorSpace?) -> String {
    guard let cs else { return "none" }
    if let n = cs.name { return n as String }
    if let icc = cs.copyICCData() as Data?, let p = ColorSyncProfileCreate(icc as CFData, nil)?.takeRetainedValue(),
       let d = ColorSyncProfileCopyDescriptionString(p)?.takeRetainedValue() {
        return "icc:" + (d as String)
    }
    return "\(cs)"
}

// Output spaces for `frames --space`: what ColorSync turns the generator's image into.
// display-p3 (default) is the Mac display space, so two images compare as they look on screen.
func outputSpace(_ name: String, image: CGImage) -> CGColorSpace? {
    switch name {
    case "display-p3": return CGColorSpace(name: CGColorSpace.displayP3)
    case "srgb": return CGColorSpace(name: CGColorSpace.sRGB)
    case "709": return CGColorSpace(name: CGColorSpace.itur_709)
    case "native": return image.colorSpace  // no conversion: the generator's own code values
    default: return nil
    }
}

func writePNG(_ image: CGImage, to url: URL, space: CGColorSpace) -> Bool {
    let w = image.width, h = image.height
    guard let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0, space: space,
                              bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else { return false }
    ctx.draw(image, in: CGRect(x: 0, y: 0, width: w, height: h))
    guard let out = ctx.makeImage(),
          let dest = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil)
    else { return false }
    CGImageDestinationAddImage(dest, out, nil)
    return CGImageDestinationFinalize(dest)
}

@MainActor
func frames() async {
    guard let at = takeValue("--at"), let outDir = takeValue("--out-dir") else { usage() }
    let prefix = takeValue("--prefix")
    let policy = takeValue("--policy") ?? "sdr"
    let spaceName = takeValue("--space") ?? "display-p3"
    guard args.count == 1, ["sdr", "source"].contains(policy),
          ["display-p3", "srgb", "709", "native"].contains(spaceName) else { usage() }
    let times = at.split(separator: ",").map { Double($0) ?? { usage() }() }
    let input = URL(fileURLWithPath: args[0])
    let dir = URL(fileURLWithPath: outDir)
    try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
    let stem = prefix ?? input.deletingPathExtension().lastPathComponent
    let gen = AVAssetImageGenerator(asset: AVURLAsset(url: input))
    gen.appliesPreferredTrackTransform = true
    gen.requestedTimeToleranceBefore = .zero
    gen.requestedTimeToleranceAfter = .zero
    gen.dynamicRangePolicy = policy == "sdr" ? .forceSDR : .matchSource
    var rows: [[String: Any]] = []
    var bad = 0
    for t in times {
        do {
            let (img, actual) = try await gen.image(at: CMTime(seconds: t, preferredTimescale: 6000))
            let f = dir.appendingPathComponent(String(format: "%@_%.3f.png", stem, t))
            guard let space = outputSpace(spaceName, image: img) else { fail("image has no color space") }
            let ok = writePNG(img, to: f, space: space)
            if !ok { bad += 1 }
            rows.append(["t": t, "actual_t": actual.seconds, "file": f.path, "ok": ok,
                         "image_color_space": describe(img.colorSpace), "png_color_space": describe(space),
                         "width": img.width, "height": img.height, "bits": img.bitsPerComponent])
        } catch {
            bad += 1
            rows.append(["t": t, "ok": false, "error": error.localizedDescription])
        }
    }
    emit(["tool": "apple-sdr", "version": version, "input": input.path, "policy": policy, "space": spaceName,
          "frames": rows])
    if bad > 0 { exit(1) }
}

switch command {
case "convert": await convert()
case "frames": await frames()
case "-h", "--help": usage()
default: usage()
}
