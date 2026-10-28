import Foundation
import CoreGraphics
import ImageIO

let root = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let clips = try JSONSerialization.jsonObject(with: Data(contentsOf: root.appendingPathComponent("clips.json"))) as! [[String: Any]]
func load(_ url: URL) -> CGImage {
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else { fatalError("Unreadable frame: \(url.path)") }
    return image
}
func save(_ context: CGContext, _ url: URL) {
    let out = CGImageDestinationCreateWithURL(url as CFURL, "public.png" as CFString, 1, nil)!
    CGImageDestinationAddImage(out, context.makeImage()!, nil)
    guard CGImageDestinationFinalize(out) else { fatalError("Cannot write frame") }
}
func context(_ width: Int, _ height: Int) -> CGContext {
    let ctx = CGContext(data: nil, width: width, height: height, bitsPerComponent: 8,
        bytesPerRow: width * 4, space: CGColorSpaceCreateDeviceRGB(),
        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    ctx.interpolationQuality = .high
    ctx.clear(CGRect(x: 0, y: 0, width: width, height: height))
    return ctx
}
for clip in clips {
    let id = clip["id"] as! String, count = clip["frames"] as! Int
    let auxiliary: String? = "detail"
    let combined = root.appendingPathComponent("combined-frames-" + id, isDirectory: true)
    let preview = root.appendingPathComponent("preview-frames-" + id, isDirectory: true)
    try FileManager.default.createDirectory(at: preview, withIntermediateDirectories: true)
    if auxiliary != nil { try FileManager.default.createDirectory(at: combined, withIntermediateDirectories: true) }
    for index in 0..<count {
        autoreleasepool {
            let filename = String(format: "%04d.png", index)
            let main = load(root.appendingPathComponent("frames-\(id)/\(filename)"))
            var image = main
            if let angle = auxiliary {
                let extra = load(root.appendingPathComponent("frames-\(id)-\(angle)/\(filename)"))
                let ctx = context(1536, 768)
                ctx.draw(main, in: CGRect(x: 0, y: 0, width: 768, height: 768))
                ctx.draw(extra, in: CGRect(x: 768, y: 0, width: 768, height: 768))
                save(ctx, combined.appendingPathComponent(filename)); image = ctx.makeImage()!
            }
            if index % 2 == 0 {
                let width = auxiliary == nil ? 384 : 640, height = auxiliary == nil ? 384 : 320
                let ctx = context(width, height)
                ctx.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
                save(ctx, preview.appendingPathComponent(String(format: "%04d.png", index / 2)))
            }
        }
    }
    print("Composed \(id): \(count) source frames, auxiliary \(auxiliary ?? "none")")
}
