import AppKit
import CoreImage
let input = FileHandle.standardInput.readDataToEndOfFile()
guard input.count > 0 && input.count < 2048,
      let filter = CIFilter(name: "CIQRCodeGenerator") else { exit(1) }
filter.setValue(input, forKey: "inputMessage")
filter.setValue("M", forKey: "inputCorrectionLevel")
guard let output = filter.outputImage,
      let cg = CIContext().createCGImage(output.transformed(by: CGAffineTransform(scaleX: 6, y: 6)), from: output.extent.applying(CGAffineTransform(scaleX: 6, y: 6))) else { exit(2) }
let bitmap = NSBitmapImageRep(cgImage: cg)
guard let png = bitmap.representation(using: .png, properties: [:]) else { exit(3) }
FileHandle.standardOutput.write(png)
