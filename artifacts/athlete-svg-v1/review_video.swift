import Foundation
import AVFoundation
import CoreGraphics
import ImageIO

let root = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let generator = AVAssetImageGenerator(asset: AVURLAsset(url: root.appendingPathComponent("5965-svg.mp4")))
generator.appliesPreferredTrackTransform = true
generator.requestedTimeToleranceBefore = .zero
generator.requestedTimeToleranceAfter = .zero
let context = CGContext(data: nil, width: 960, height: 305, bitsPerComponent: 8, bytesPerRow: 3840,
    space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
for (index, seconds) in [0.0, 2.6, 5.16].enumerated() {
    let image = try generator.copyCGImage(at: CMTime(seconds: seconds, preferredTimescale: 600), actualTime: nil)
    context.draw(image, in: CGRect(x: index * 320, y: 0, width: 320, height: 305))
}
let destination = CGImageDestinationCreateWithURL(root.appendingPathComponent("mp4-review.png") as CFURL, "public.png" as CFString, 1, nil)!
CGImageDestinationAddImage(destination, context.makeImage()!, nil)
guard CGImageDestinationFinalize(destination) else { fatalError("Cannot save decoded review") }
print("Decoded opening, middle and closing frames")
