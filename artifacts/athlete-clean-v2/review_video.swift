import Foundation
import AVFoundation
import AppKit
import ImageIO

let root = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let asset = AVURLAsset(url: root.appendingPathComponent("muscle-movements-preview.mp4"))
let generator = AVAssetImageGenerator(asset: asset)
generator.appliesPreferredTrackTransform = true
generator.requestedTimeToleranceBefore = .zero
generator.requestedTimeToleranceAfter = .zero
let times: [Double] = [0, 2.6, 5.2, 6.8, 8.4, 10.0]
let context = CGContext(data: nil, width: 960, height: 640, bitsPerComponent: 8,
    bytesPerRow: 960 * 4, space: CGColorSpaceCreateDeviceRGB(),
    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
for (index, time) in times.enumerated() {
    let image = try generator.copyCGImage(at: CMTime(seconds: time, preferredTimescale: 600), actualTime: nil)
    context.draw(image, in: CGRect(x: (index % 3) * 320, y: (1 - index / 3) * 320, width: 320, height: 320))
}
let output = root.appendingPathComponent("mp4-review.png")
let destination = CGImageDestinationCreateWithURL(output as CFURL, "public.png" as CFString, 1, nil)!
CGImageDestinationAddImage(destination, context.makeImage()!, nil)
guard CGImageDestinationFinalize(destination) else { fatalError("Could not save video review") }
print(output.path)
