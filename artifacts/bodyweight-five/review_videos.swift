import Foundation
import AVFoundation
import CoreGraphics
import ImageIO
import CryptoKit

let root = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let clips = try JSONSerialization.jsonObject(with: Data(contentsOf: root.appendingPathComponent("clips.json"))) as! [[String: Any]]
func writePNG(_ image: CGImage, _ url: URL) {
    let output = CGImageDestinationCreateWithURL(url as CFURL, "public.png" as CFString, 1, nil)!
    CGImageDestinationAddImage(output, image, nil)
    guard CGImageDestinationFinalize(output) else { fatalError("Cannot write decoded review") }
}
func pixels(_ image: CGImage) -> [UInt8] {
    var bytes = [UInt8](repeating: 0, count: 160 * 160 * 4)
    bytes.withUnsafeMutableBytes { memory in
        let ctx = CGContext(data: memory.baseAddress, width: 160, height: 160, bitsPerComponent: 8,
            bytesPerRow: 640, space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
        ctx.draw(image, in: CGRect(x: 0, y: 0, width: 160, height: 160))
    }
    return bytes
}
func difference(_ a: [UInt8], _ b: [UInt8]) -> Double {
    var sum = 0
    for index in a.indices where index % 4 != 3 { sum += abs(Int(a[index]) - Int(b[index])) }
    return Double(sum) / Double(160 * 160 * 3 * 255)
}
var reports: [[String: Any]] = []
for clip in clips {
    let id = clip["id"] as! String, count = clip["frames"] as! Int
    let expected = clip["duration"] as! Double
    let url = root.appendingPathComponent(id + ".mp4"), data = try Data(contentsOf: url)
    let asset = AVURLAsset(url: url)
    guard let track = asset.tracks(withMediaType: .video).first else { fatalError("Missing video \(id)") }
    let duration = CMTimeGetSeconds(asset.duration), size = track.naturalSize
    guard abs(duration - expected) < 0.01 && abs(track.nominalFrameRate - 30) < 0.01 else { fatalError("Rate/duration mismatch \(id)") }
    guard size.height == 768 && size.width == 1536 else { fatalError("Size mismatch \(id)") }
    guard asset.tracks(withMediaType: .audio).isEmpty else { fatalError("Unexpected audio \(id)") }
    let generator = AVAssetImageGenerator(asset: asset)
    generator.appliesPreferredTrackTransform = true
    generator.requestedTimeToleranceBefore = .zero; generator.requestedTimeToleranceAfter = .zero
    let samples = Set([0, count / 4, count / 2, 3 * count / 4, count - 1])
    let sheet = CGContext(data: nil, width: 1920, height: 384, bitsPerComponent: 8,
        bytesPerRow: 7680, space: CGColorSpaceCreateDeviceRGB(),
        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    sheet.setFillColor(CGColor(gray: 1, alpha: 1)); sheet.fill(CGRect(x: 0, y: 0, width: 1920, height: 384))
    var first: [UInt8] = [], previous: [UInt8] = [], deltas: [Double] = [], tile = 0
    for index in 0..<count {
        let image = try generator.copyCGImage(at: CMTime(value: Int64(index), timescale: 30), actualTime: nil)
        let current = pixels(image)
        if index == 0 { first = current } else { deltas.append(difference(previous, current)) }
        previous = current
        if samples.contains(index) {
            let height = 384.0 * Double(image.height) / Double(image.width)
            sheet.draw(image, in: CGRect(x: Double(tile * 384), y: (384 - height) / 2, width: 384, height: height)); tile += 1
            if index == count / 2 { writePNG(image, root.appendingPathComponent("decoded-\(id)-mid.png")) }
        }
    }
    let wrap = difference(previous, first), maximum = deltas.max() ?? 0
    guard wrap <= max(0.001, maximum * 1.8) else { fatalError("Loop discontinuity \(id): \(wrap) vs \(maximum)") }
    writePNG(sheet.makeImage()!, root.appendingPathComponent("decoded-\(id)-sheet.png"))
    reports.append(["id": id, "file": url.lastPathComponent, "sha256": SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined(),
        "bytes": data.count, "duration_seconds": duration, "fps": track.nominalFrameRate,
        "width": size.width, "height": size.height, "audio_tracks": 0,
        "all_frames_decoded": count, "loop_boundary_rgb_difference": wrap,
        "max_adjacent_frame_rgb_difference": maximum, "decoded_sample_frames": samples.sorted()])
    print("Decoded \(id): \(count) frames; wrap \(wrap), largest adjacent change \(maximum)")
}
let report: [String: Any] = ["ok": true, "scope": "Actual delivered MP4 metadata and every frame decoded; pixel loop check is not a biomechanics certification", "clips": reports]
try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
    .write(to: root.appendingPathComponent("video-review.json"))
