import Foundation
import AVFoundation
import CoreGraphics
import ImageIO

let root = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let asset = AVURLAsset(url: root.appendingPathComponent("human-squat.mp4"))
let tracks = asset.tracks(withMediaType: .video)
guard let track = tracks.first else { fatalError("Video track missing") }
let seconds = CMTimeGetSeconds(asset.duration)
let generator = AVAssetImageGenerator(asset: asset)
generator.appliesPreferredTrackTransform = true
generator.requestedTimeToleranceBefore = .zero
generator.requestedTimeToleranceAfter = .zero
let context = CGContext(data: nil, width: 960, height: 320, bitsPerComponent: 8,
    bytesPerRow: 3840, space: CGColorSpaceCreateDeviceRGB(),
    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
let samples = [0.0, 34.0 / 30.0, 67.0 / 30.0]
for (index, time) in samples.enumerated() {
    let image = try generator.copyCGImage(at: CMTime(seconds: time, preferredTimescale: 30000), actualTime: nil)
    guard image.width == 640 && image.height == 640 else { fatalError("Unexpected decoded dimensions") }
    context.draw(image, in: CGRect(x: index * 320, y: 0, width: 320, height: 320))
}
let destination = CGImageDestinationCreateWithURL(root.appendingPathComponent("mp4-review.png") as CFURL, "public.png" as CFString, 1, nil)!
CGImageDestinationAddImage(destination, context.makeImage()!, nil)
guard CGImageDestinationFinalize(destination) else { fatalError("Cannot save decoded review") }
guard abs(seconds - 68.0 / 30.0) < 0.01 && abs(track.nominalFrameRate - 30) < 0.01 else { fatalError("Unexpected duration or rate") }
// Decode every delivered frame to catch a discontinuity at the loop boundary.
func pixels(_ image: CGImage) -> [UInt8] {
    var bytes = [UInt8](repeating: 0, count: 160 * 160 * 4)
    bytes.withUnsafeMutableBytes { raw in
        let canvas = CGContext(data: raw.baseAddress, width: 160, height: 160,
            bitsPerComponent: 8, bytesPerRow: 640, space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
        canvas.draw(image, in: CGRect(x: 0, y: 0, width: 160, height: 160))
    }
    return bytes
}
func difference(_ a: [UInt8], _ b: [UInt8]) -> Double {
    var sum = 0
    for i in a.indices where i % 4 != 3 { sum += abs(Int(a[i]) - Int(b[i])) }
    return Double(sum) / Double(160 * 160 * 3 * 255)
}
var first: [UInt8] = [], previous: [UInt8] = [], deltas: [Double] = []
for frame in 0..<68 {
    let image = try generator.copyCGImage(at: CMTime(value: Int64(frame), timescale: 30), actualTime: nil)
    let current = pixels(image)
    if frame == 0 { first = current } else { deltas.append(difference(previous, current)) }
    previous = current
}
let wrapDifference = difference(previous, first)
guard wrapDifference <= (deltas.max()! * 1.5) else { fatalError("Loop boundary exceeds normal frame transitions") }
let report: [String: Any] = ["ok": true, "duration_seconds": seconds,
    "fps": track.nominalFrameRate, "width": track.naturalSize.width,
    "height": track.naturalSize.height, "audio_tracks": asset.tracks(withMediaType: .audio).count,
    "decoded_samples_seconds": samples, "all_frames_decoded": 68,
    "max_adjacent_frame_rgb_difference": deltas.max()!,
    "loop_boundary_rgb_difference": wrapDifference,
    "continuity_scope": "Pixel-difference continuity check, not a biomechanical technique assessment"]
try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
    .write(to: root.appendingPathComponent("video-review.json"))
print("Decoded opening, bottom and closing frames; 640x640, 30 fps, duration verified")
