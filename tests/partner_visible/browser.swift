import Foundation
import Cocoa
import WebKit
let ap=NSApplication.shared
ap.setActivationPolicy(.prohibited)
let path=CommandLine.arguments[1]
let port=Int(CommandLine.arguments[2])!
precondition(port>0 && port != 8780)
let origin="http://127.0.0.1:"+String(port)
let doc=try String(contentsOfFile:path,encoding:.utf8)
let config=WKWebViewConfiguration()
config.websiteDataStore = .nonPersistent()
let scenario=CommandLine.arguments[3]
let prelude = """
window.scenario='\(scenario)';
window.simLanguage='en-US';
Object.defineProperty(navigator,'languages',{get:()=>[window.simLanguage]});
window.languageWrites=0;
const originalFetch=window.fetch;
window.fetch=function(input,options){if(options && options.method && options.method.toUpperCase()!=='GET')window.languageWrites++;return originalFetch.apply(this,arguments);};
if (scenario==='legacy') localStorage.setItem('ptds-language','zh');
if (scenario==='blocked') Object.defineProperty(window,'localStorage',{get(){throw Error('storage blocked');}});
"""
config.userContentController.addUserScript(WKUserScript(source:prelude,injectionTime:.atDocumentStart,forMainFrameOnly:true))
var done=false
var view:WKWebView!
var hostWindow:NSWindow!
final class Page: NSObject, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler {
 func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping ([URL]?) -> Void) {
   let url = URL(fileURLWithPath: CommandLine.arguments[5])
   precondition(url.lastPathComponent == "sample-import.csv" && url.deletingLastPathComponent().lastPathComponent == "data")
   completionHandler([url])
 }
 func webView(_ webView:WKWebView,didFailProvisionalNavigation navigation:WKNavigation!,withError error:Error){print("FAIL_PROVISIONAL: " + error.localizedDescription);done=true}
 func webView(_ webView:WKWebView,didFail navigation:WKNavigation!,withError error:Error){print("FAIL_NAV: " + error.localizedDescription);done=true}
 func webView(_ webView:WKWebView,didFinish navigation:WKNavigation!){func verify(){webView.evaluateJavaScript(doc+";void 0",completionHandler:{_,error in if let error=error{print(error);done=true}})}
 if scenario=="unused-initial" && !FileManager.default.fileExists(atPath:CommandLine.arguments[4]) {
   webView.takeSnapshot(with:nil){img,_ in
      if let bits=img?.tiffRepresentation, let png=NSBitmapImageRep(data: bits)?.representation(using:.jpeg,properties:[.compressionFactor:0.65]) {try? png.write(to:URL(fileURLWithPath:CommandLine.arguments[4]))}
      verify()
   }
 } else { verify() }}
 func userContentController(_ userContentController:WKUserContentController, didReceive m: WKScriptMessage){
   guard m.frameInfo.isMainFrame else{return}
   if let str=m.body as? String, str.hasPrefix("shot:") {
   let name=String(str.dropFirst(5))
   guard name.range(of:"^[a-z0-9_-]{1,24}$",options:.regularExpression) != nil else {done=true;return}
   view.takeSnapshot(with:nil){img,err in
     if let image=img, let bits=image.tiffRepresentation, let png=NSBitmapImageRep(data:bits)?.representation(using:.jpeg,properties:[.compressionFactor:0.65]) {
       do { try png.write(to:URL(fileURLWithPath:CommandLine.arguments[4]).appendingPathComponent(name+".jpg"))
         view.evaluateJavaScript("window.__shotDone()", completionHandler:nil)
       } catch { print("SNAPSHOT_WRITE_ERROR");done=true }
     } else { print("SNAPSHOT_FAILED");done=true }
   }
   return
 }
 if let str=m.body as? String, str.hasPrefix("step:"){FileHandle.standardError.write(Data((str + ";").utf8));return}
   if let str=m.body as? String, str.hasPrefix("delay:"),let ms=Int(str.dropFirst(6)){DispatchQueue.main.asyncAfter(deadline:.now() + .milliseconds(min(1000,ms))){view.evaluateJavaScript("if(window.__ptdsTestWake)window.__ptdsTestWake();void 0")};return}
   print(String(describing:m.body)); done=true
 }
 func webView(_ webView:WKWebView,decidePolicyFor action:WKNavigationAction, decisionHandler:@escaping(WKNavigationActionPolicy)->Void){decisionHandler((action.request.url?.absoluteString == origin+"/" && action.request.httpMethod == "GET") ? .allow : .cancel)}
}
let owner=Page()
config.userContentController.add(owner,name:"fixtureResult")

let rules="""
[{"trigger":{"url-filter":".*"},"action":{"type":"block"}},{"trigger":{"url-filter":"^http://127[.]0[.]0[.]1:\(port)/"},"action":{"type":"ignore-previous-rules"}},{"trigger":{"url-filter":"^blob:http://127[.]0[.]0[.]1:\(port)/"},"action":{"type":"ignore-previous-rules"}}]
"""
WKContentRuleListStore.default().compileContentRuleList(forIdentifier:"PTDSFictionalNoNetwork",encodedContentRuleList:rules){list,error in
guard let list=list,error==nil else{print("BLOCKER_UNAVAILABLE");done=true;return}
config.userContentController.add(list)
view=WKWebView(frame:NSRect(x:0,y:0,width:1100,height:780),configuration:config)
hostWindow=NSWindow(contentRect:NSRect(x:-5000,y:60,width:1100,height:780),styleMask:[.borderless],backing:.buffered,defer:false)
hostWindow.isReleasedWhenClosed=false
hostWindow.contentView=view
hostWindow.orderBack(nil)
view.navigationDelegate=owner; view.uiDelegate=owner
view.load(URLRequest(url:URL(string:origin+"/")!))
}
let end=Date(timeIntervalSinceNow:120)
while !done && Date()<end{RunLoop.main.run(until:Date(timeIntervalSinceNow:0.05))}
if !done {print("TIMEOUT");exit(2)}
