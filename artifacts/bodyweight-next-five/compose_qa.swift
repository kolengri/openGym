// Compose five curated QA sheets from independent views, never frame sequences.
import AppKit
import Foundation

let root = URL(fileURLWithPath: CommandLine.arguments[1])
let ids = ["5265", "4007", "6428", "10565", "6560"]
for id in ids {
    let width = 1800, height = 1260
    let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: width, pixelsHigh: height,
        bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
        colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    let context = NSGraphicsContext(bitmapImageRep: bitmap)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = context
    NSColor(calibratedWhite: 0.92, alpha: 1).setFill()
    NSBezierPath(rect: NSRect(x: 0, y: 0, width: width, height: height)).fill()
    for (row, mode) in ["solid", "wire"].enumerated() {
        for (column, view) in ["oblique", "side", "rear"].enumerated() {
            let path = root.appendingPathComponent("qa/stills/\(id)-\(view)-\(mode).png")
            guard let image = NSImage(contentsOf: path) else { fatalError("Missing QA still \(path)") }
            let y = (1 - row) * 630
            image.draw(in: NSRect(x: column * 600, y: y, width: 600, height: 600))
            let frame = view == "side" ? 0 : view == "oblique" ? (id == "5265" ? 60 : ["4007", "6428"].contains(id) ? 45 : 60) : ["10565", "6560"].contains(id) ? 420 : id == "5265" ? 180 : 135
            let label = "\(id) · \(view) · \(mode) · source frame \(frame)" as NSString
            label.draw(at: NSPoint(x: column * 600 + 12, y: y + 605), withAttributes: [
                .font: NSFont.monospacedSystemFont(ofSize: 16, weight: .medium),
                .foregroundColor: NSColor.black])
        }
    }
    context.flushGraphics()
    NSGraphicsContext.restoreGraphicsState()
    try bitmap.representation(using: .png, properties: [:])!.write(to: root.appendingPathComponent("qa/\(id)-solid-wire-sheet.png"))
}
