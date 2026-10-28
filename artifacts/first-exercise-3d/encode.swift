import Foundation
import AVFoundation
import CoreGraphics
import CoreVideo
import ImageIO

guard (4...5).contains(CommandLine.arguments.count) else { fatalError("Usage: swift encode.swift <PNG directory> <output.mp4> <fps> [bitrate]") }
let directory = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let output = URL(fileURLWithPath: CommandLine.arguments[2])
let fps = Int32(CommandLine.arguments[3])!
let frames = try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
    .filter { $0.pathExtension == "png" }.sorted { $0.lastPathComponent < $1.lastPathComponent }
guard !frames.isEmpty, let firstSource = CGImageSourceCreateWithURL(frames[0] as CFURL, nil),
      let first = CGImageSourceCreateImageAtIndex(firstSource, 0, nil) else { fatalError("No readable PNG frames") }
let width = first.width, height = first.height
if FileManager.default.fileExists(atPath: output.path) { try FileManager.default.removeItem(at: output) }
let writer = try AVAssetWriter(outputURL: output, fileType: .mp4)
let settings: [String: Any] = [
    AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: width, AVVideoHeightKey: height,
    AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: CommandLine.arguments.count == 5 ? Int(CommandLine.arguments[4])! : 4_000_000, AVVideoMaxKeyFrameIntervalKey: Int(fps)]
]
let input = AVAssetWriterInput(mediaType: .video, outputSettings: settings)
input.expectsMediaDataInRealTime = false
let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
    kCVPixelBufferWidthKey as String: width, kCVPixelBufferHeightKey as String: height,
    kCVPixelBufferCGImageCompatibilityKey as String: true,
    kCVPixelBufferCGBitmapContextCompatibilityKey as String: true
])
guard writer.canAdd(input) else { fatalError("Cannot add video input") }
writer.add(input)
guard writer.startWriting() else { fatalError("Cannot start writer") }
writer.startSession(atSourceTime: .zero)
for (index, url) in frames.enumerated() {
    while !input.isReadyForMoreMediaData { if writer.status == .failed { fatalError(String(describing: writer.error)) }; usleep(1000) }
    autoreleasepool {
        guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
              let image = CGImageSourceCreateImageAtIndex(source, 0, nil),
              image.width == width, image.height == height,
              let pool = adaptor.pixelBufferPool else { fatalError("Invalid source frame") }
        var buffer: CVPixelBuffer?
        guard CVPixelBufferPoolCreatePixelBuffer(nil, pool, &buffer) == kCVReturnSuccess,
              let pixelBuffer = buffer else { fatalError("Cannot allocate frame") }
        CVPixelBufferLockBaseAddress(pixelBuffer, [])
        let flags = CGBitmapInfo.byteOrder32Little.rawValue | CGImageAlphaInfo.premultipliedFirst.rawValue
        guard let context = CGContext(data: CVPixelBufferGetBaseAddress(pixelBuffer), width: width, height: height,
            bitsPerComponent: 8, bytesPerRow: CVPixelBufferGetBytesPerRow(pixelBuffer),
            space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: flags) else { fatalError("Cannot create pixel context") }
        context.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
        CVPixelBufferUnlockBaseAddress(pixelBuffer, [])
        guard adaptor.append(pixelBuffer, withPresentationTime: CMTime(value: Int64(index), timescale: fps)) else {
            fatalError(String(describing: writer.error))
        }
    }
}
writer.endSession(atSourceTime: CMTime(value: Int64(frames.count), timescale: fps))
input.markAsFinished()
let done = DispatchSemaphore(value: 0)
writer.finishWriting { done.signal() }
done.wait()
guard writer.status == .completed else { fatalError(String(describing: writer.error)) }
let asset = AVURLAsset(url: output)
guard let track = asset.tracks(withMediaType: .video).first else { fatalError("Missing video track") }
let info: [String: Any] = [
    "file": output.path, "frames": frames.count, "width": width, "height": height,
    "fps": track.nominalFrameRate, "duration_seconds": asset.duration.seconds,
    "audio": !asset.tracks(withMediaType: .audio).isEmpty,
    "bytes": (try Data(contentsOf: output)).count, "renderer": "Three.js", "encoder": "AVFoundation H.264"
]
let json = try JSONSerialization.data(withJSONObject: info, options: [.prettyPrinted, .sortedKeys])
try json.write(to: output.deletingPathExtension().appendingPathExtension("json"))
print(String(decoding: json, as: UTF8.self))
