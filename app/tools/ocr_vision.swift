// PTDS 本机识别：macOS Vision 读图片或 PDF 里的文字，输出 JSON（每段文字 + 位置 + 置信度）。不联网。
//   swiftc -O app/tools/ocr_vision.swift -o <bin>     （服务第一次用时自动编译）
//   <bin> 化验单.png|化验单.pdf            → stdout: {"engine":..., "items":[{page,text,conf,x,y,w,h}]}
//   <bin> 化验单.pdf --page N               → 只读第 N 页（大 PDF 一页一页读，一次只渲染一页）
//   <bin> --count 化验单.pdf                → stdout: 页数
//   <bin> --render-sample out.png           → 画一张合成化验单，供自检
import AppKit
import Foundation
import PDFKit
import Vision

struct Item: Codable { let page: Int; let text: String; let conf: Float; let x: Double; let y: Double; let w: Double; let h: Double }
struct Out: Codable { let engine: String; let pages: Int; let tiles: Int; let items: [Item] }

var gItems: [Item] = []
var gTiles = 0

func pdfPage(_ doc: PDFDocument, _ i: Int) -> CGImage? {
    guard let page = doc.page(at: i) else { return nil }
    let box = page.bounds(for: .mediaBox)
    let scale: CGFloat = 2.5
    let size = NSSize(width: box.width * scale, height: box.height * scale)
    let img = NSImage(size: size)
    img.lockFocus()
    NSColor.white.setFill()
    NSRect(origin: .zero, size: size).fill()
    if let ctx = NSGraphicsContext.current?.cgContext {
        ctx.scaleBy(x: scale, y: scale)
        page.draw(with: .mediaBox, to: ctx)
    }
    img.unlockFocus()
    var rect = NSRect(origin: .zero, size: size)
    return img.cgImage(forProposedRect: &rect, context: nil, hints: nil)
}

func cgImages(_ url: URL) -> [CGImage] {
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
          let cg = CGImageSourceCreateImageAtIndex(src, 0, nil) else { return [] }
    return [cg]
}

func vision(_ cg: CGImage) -> [VNRecognizedTextObservation] {
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = false  // 数值保持原样，不让引擎"纠正"
    req.recognitionLanguages = ["zh-Hans", "en-US"]
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    try? handler.perform([req])
    return req.results ?? []
}

// 超长手机截图（高 > 宽的 2.2 倍）：整张交给 Vision 会被缩小、小字读不清，所以切成几段（相邻两段重叠 20%）分别识别，
// 坐标换回整张图；重叠区里的字只算一次（每段只保留中心落在自己那一段的字）。
func bands(_ W: Double, _ H: Double) -> [(Double, Double, Double, Double)] {
    if H <= 2.2 * W { return [(0, H, 0, H)] }
    let th = (1.4 * W).rounded(), ov = (0.2 * th).rounded()
    var out: [(Double, Double, Double, Double)] = []
    var top = 0.0
    while true {
        let h = min(th, H - top)
        let last = top + h >= H
        out.append((top, h, top == 0 ? 0 : top + ov / 2, last ? H : top + h - ov / 2))
        if last { break }
        top += th - ov
    }
    return out
}

func readImage(_ cg: CGImage, _ pageNo: Int) {
    let W = Double(cg.width), H = Double(cg.height)
    let parts = bands(W, H)
    for (t, th, k0, k1) in parts {
        let tile: CGImage? = parts.count == 1 ? cg : cg.cropping(to: CGRect(x: 0, y: t, width: W, height: th))
        guard let img = tile else { continue }
        gTiles += 1
        for obs in vision(img) {
            guard let top = obs.topCandidates(1).first else { continue }
            let b = obs.boundingBox  // normalized, origin bottom-left
            let topPx = t + (1 - Double(b.maxY)) * th
            let hPx = Double(b.height) * th
            let cy = topPx + hPx / 2
            if cy < k0 || cy >= k1 { continue }
            gItems.append(Item(page: pageNo, text: top.string, conf: top.confidence,
                               x: Double(b.minX), y: topPx / H, w: Double(b.width), h: hPx / H))
        }
    }
}

func recognize(_ url: URL, only: Int) -> Out {
    var pages = 0
    if url.pathExtension.lowercased() == "pdf", let doc = PDFDocument(url: url) {
        let wanted = only > 0 ? [only - 1] : Array(0..<doc.pageCount)
        for i in wanted where i >= 0 && i < doc.pageCount {
            autoreleasepool {  // 一次只留一页的图在内存里
                if let cg = pdfPage(doc, i) { readImage(cg, i + 1) }
            }
            pages += 1
        }
    } else {
        let images = cgImages(url)
        for (index, cg) in images.enumerated() { readImage(cg, index + 1) }
        pages = images.count
    }
    let os = ProcessInfo.processInfo.operatingSystemVersionString
    return Out(engine: "macOS Vision VNRecognizeTextRequest (accurate) · " + os, pages: pages, tiles: gTiles, items: gItems)
}

func renderSample(_ path: String) {
    let size = NSSize(width: 1240, height: 900)
    let img = NSImage(size: size)
    img.lockFocus()
    NSColor.white.setFill(); NSRect(origin: .zero, size: size).fill()
    let font = NSFont(name: "PingFang SC", size: 30) ?? NSFont.systemFont(ofSize: 30)
    let attrs: [NSAttributedString.Key: Any] = [.font: font, .foregroundColor: NSColor.black]
    let lines: [(String, String, String, String)] = [
        ("PTDS 自检 · 合成化验单（非真实数据）", "", "", ""),
        ("采样时间：2026-10-04 08:00", "", "", ""),
        ("项目", "结果", "单位", "参考范围"),
        ("铁蛋白", "1520", "ng/mL", "30-400"),
        ("血小板计数", "98", "×10^9/L", "125-350"),
        ("白细胞计数", "6.2", "×10^9/L", "3.5-9.5"),
        ("C反应蛋白", "18", "mg/L", "0-10"),
        ("谷草转氨酶", "65", "U/L", "15-40"),
        ("甘油三酯", "2.30", "mmol/L", "<1.7"),
    ]
    for (i, l) in lines.enumerated() {
        let y = size.height - 80 - CGFloat(i) * 80
        (l.0 as NSString).draw(at: NSPoint(x: 60, y: y), withAttributes: attrs)
        (l.1 as NSString).draw(at: NSPoint(x: 520, y: y), withAttributes: attrs)
        (l.2 as NSString).draw(at: NSPoint(x: 720, y: y), withAttributes: attrs)
        (l.3 as NSString).draw(at: NSPoint(x: 960, y: y), withAttributes: attrs)
    }
    img.unlockFocus()
    guard let tiff = img.tiffRepresentation, let rep = NSBitmapImageRep(data: tiff),
          let png = rep.representation(using: .png, properties: [:]) else { exit(2) }
    try? png.write(to: URL(fileURLWithPath: path))
}

let args = CommandLine.arguments
// Read-only original-page preview; no OCR or extracted-field reconstruction.
if args.count == 4 && args[1] == "--preview", let n = Int(args[3]), n > 0,
   let doc = PDFDocument(url: URL(fileURLWithPath: args[2])), n <= doc.pageCount,
   let page = doc.page(at: n - 1) {
    let image = page.thumbnail(of: NSSize(width: 1800, height: 2400), for: .mediaBox)
    guard let tiff = image.tiffRepresentation, let rep = NSBitmapImageRep(data: tiff),
          let png = rep.representation(using: .png, properties: [:]) else { exit(2) }
    FileHandle.standardOutput.write(png)
    exit(0)
}
if args.count > 1 && args[1] == "--preview" { exit(2) }
if args.count == 3 && args[1] == "--render-sample" { renderSample(args[2]); exit(0) }
if args.count == 3 && args[1] == "--count" {
    let n = PDFDocument(url: URL(fileURLWithPath: args[2]))?.pageCount ?? 0
    FileHandle.standardOutput.write(String(n).data(using: .utf8)!)
    exit(n > 0 ? 0 : 2)
}
var only = 0
if args.count == 4 && args[2] == "--page", let n = Int(args[3]) { only = n }
guard args.count == 2 || only > 0 else { FileHandle.standardError.write("usage: ocr_vision FILE [--page N] | --count FILE\n".data(using: .utf8)!); exit(64) }
let out = recognize(URL(fileURLWithPath: args[1]), only: only)
let enc = JSONEncoder()
FileHandle.standardOutput.write(try! enc.encode(out))
