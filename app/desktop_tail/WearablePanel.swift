// Native window ownership only; its content is the same local HTML/CSS as the browser tail.
import AppKit
import WebKit

final class LocalSession: NSObject, URLSessionTaskDelegate {
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) { completionHandler(nil) }
}
final class TailWebView: WKWebView { override func acceptsFirstMouse(for event:NSEvent?) -> Bool { true } }
final class ReadingsPanel: NSPanel { override var canBecomeKey: Bool { true } }
final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate, WKScriptMessageHandler, WKNavigationDelegate {
    var panel: ReadingsPanel!; var web: WKWebView!; var timer: Timer?; var dragTimer: Timer?
    var url: URL!; var fetching=false; var pinned=true; var appliedPinRevision=0; var loaded=false
    var lastSize=""; var displayScale=1.0; var shareKey:String?; var isPillbox=false; var finding=false
    let redirectGuard=LocalSession()
    lazy var session: URLSession = { let c=URLSessionConfiguration.ephemeral; c.timeoutIntervalForRequest=5; c.requestCachePolicy = .reloadIgnoringLocalCacheData; return URLSession(configuration:c,delegate:redirectGuard,delegateQueue:nil) }()
    func applicationDidFinishLaunching(_ notification: Notification) {
        guard CommandLine.arguments.count>=2, let target=URL(string:CommandLine.arguments[1]), target.scheme=="http", target.host == "127.0.0.1", target.port != nil, target.user==nil,target.password==nil,target.path=="/api/desktop-tail/data",
              let file=Bundle.main.url(forResource:"panel",withExtension:"html"), let html=try? String(contentsOf:file,encoding:.utf8) else { NSApp.terminate(nil); return }
        url=target
        panel=ReadingsPanel(contentRect:NSRect(x:0,y:0,width:300,height:274),styleMask:[.borderless,.nonactivatingPanel],backing:.buffered,defer:false)
        panel.title="PTDS · 近期读数"; panel.isFloatingPanel=true; panel.hidesOnDeactivate = false
        panel.becomesKeyOnlyIfNeeded=false; panel.isReleasedWhenClosed=false; panel.isOpaque=false; panel.backgroundColor = .clear; panel.hasShadow=true; panel.delegate=self
        let config=WKWebViewConfiguration(); config.websiteDataStore = .nonPersistent(); config.preferences.minimumFontSize=0; config.userContentController.add(self,name:"tail")
        web=TailWebView(frame:panel.contentView!.bounds,configuration:config); web.autoresizingMask=[.width,.height]; web.navigationDelegate=self; web.setValue(false,forKey:"drawsBackground"); panel.contentView=web
        if let screen=NSScreen.main { let f=screen.visibleFrame; panel.setFrameOrigin(NSPoint(x:f.maxX-324,y:f.minY+32)) }
        applyPin(); web.loadHTMLString(html,baseURL:nil)
        timer=Timer.scheduledTimer(withTimeInterval:3,repeats:true){[weak self] _ in self?.fetch()}
    }
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy)->Void) {
        decisionHandler(!loaded && action.request.url?.absoluteString == "about:blank" ? .allow : .cancel)
    }
    func applyPin(){
        panel.level = pinned ? .floating : .normal
        panel.collectionBehavior = pinned ? [.canJoinAllSpaces,.fullScreenAuxiliary] : [.managed]
        if #available(macOS 13.0,*),pinned {panel.collectionBehavior.insert(.canJoinAllApplications)}
        if loaded {web.callAsyncJavaScript("window.tailPin(value)",arguments:["value":pinned],in:nil,in:.page,completionHandler:nil)}
    }
    func userContentController(_ userContentController: WKUserContentController,didReceive message:WKScriptMessage){
        guard message.frameInfo.isMainFrame, let d=message.body as? [String:Any],let action=d["action"] as? String else{return}
        switch action {
        case "ready": loaded=true;fetch()
        case "pin": pinned.toggle();applyPin();print("PTDS_PANEL_PIN pinned=\(pinned) level=\(panel.level.rawValue)");fflush(stdout)
        case "close": panel.close()
        case "show": var c=URLComponents(url:url,resolvingAgainstBaseURL:false)!;c.path="/";c.query=nil;if let local=c.url{NSWorkspace.shared.open(local)}
        case "find": findPillbox()
        case "share":
            guard let key=shareKey else{return}
            var c=URLComponents(url:url,resolvingAgainstBaseURL:false)!;c.path="/";c.query=nil;c.fragment="phone-tail="+key
            if let local=c.url{NSWorkspace.shared.open(local)}
        case "drag":
            let origin=panel.frame.origin,start=NSEvent.mouseLocation
            dragTimer?.invalidate();dragTimer=Timer.scheduledTimer(withTimeInterval:0.016,repeats:true){[weak self] t in
                guard let self,NSEvent.pressedMouseButtons & 1 != 0 else{t.invalidate();return}
                let now=NSEvent.mouseLocation;self.panel.setFrameOrigin(NSPoint(x:origin.x+now.x-start.x,y:origin.y+now.y-start.y))
            }
        case "size":
            guard let w=d["width"] as? Double,let h=d["height"] as? Double,w.isFinite,h.isFinite,w>=200,w<=600,h>=100,h<=900 else{return}
            let old=panel.frame,newSize=NSSize(width:w*displayScale,height:ceil(h*displayScale*2)/2);panel.setFrame(NSRect(x:old.minX,y:old.maxY-newSize.height,width:newSize.width,height:newSize.height),display:true)
            let size="\(w)x\(h)";if size != lastSize {lastSize=size;if let bytes=try? JSONSerialization.data(withJSONObject:d,options:[.sortedKeys]),let log=String(data:bytes,encoding:.utf8){print("PTDS_PANEL_GEOMETRY \(log)")};fflush(stdout)}
            if !panel.isVisible {panel.orderFrontRegardless();print("PTDS_PANEL_READY level=\(panel.level.rawValue) hidesOnDeactivate=\(panel.hidesOnDeactivate)");fflush(stdout)}
        default:break
        }
    }
    func fetch(){
        guard loaded && !fetching else{return};fetching=true
        session.dataTask(with:url){[weak self] data,response,error in
            let payload=(response as? HTTPURLResponse)?.statusCode==200 ? data.flatMap{try? JSONSerialization.jsonObject(with:$0) as? [String:Any]}:nil
            DispatchQueue.main.async{
                guard let self else{return};self.fetching=false
                guard let payload, (payload["device"] as? String == "pillbox" || (payload["tiles"] as? [[String:Any]])?.count == 4) else{self.web.evaluateJavaScript("window.tailOffline()",completionHandler:nil);return}
                self.isPillbox=payload["device"] as? String == "pillbox"
                self.shareKey=payload["device"] as? String == "somaloop" ? payload["share_key"] as? String : nil
                self.panel.title="PTDS · \(payload["name"] as? String ?? "可穿戴") 近期读数"
                if let visual=payload["visual"] as? [String:Any],let width=visual["width"] as? Double,width>=200,width<=600 {
                    let ratio=visual["pixelRatio"] as? Double ?? 2
                    self.displayScale=max(0.25,min(4,ratio/(self.panel.screen?.backingScaleFactor ?? 2)))
                    self.web.pageZoom=1
                    if abs(self.panel.frame.width-width*self.displayScale)>0.1 {self.panel.setContentSize(NSSize(width:(width*self.displayScale*2).rounded()/2,height:self.panel.frame.height))}
                }
                if let revision=payload["pin_revision"] as? Int,revision>self.appliedPinRevision {self.appliedPinRevision=revision;self.pinned=true;self.applyPin();if self.panel.isVisible{self.panel.orderFrontRegardless()}}
                var rendered=payload;rendered["displayScale"]=self.displayScale
                self.web.callAsyncJavaScript("window.tailUpdate(payload)",arguments:["payload":rendered],in:nil,in:.page,completionHandler:nil)
            }
        }.resume()
    }
    func findPillbox(){
        guard isPillbox && !finding else{return};finding=true
        var c=URLComponents(url:url,resolvingAgainstBaseURL:false)!;c.path="/api/desktop-tail/find"
        var request=URLRequest(url:c.url!);request.httpMethod="POST";request.setValue("1",forHTTPHeaderField:"X-PTDS");request.setValue("application/json",forHTTPHeaderField:"Content-Type");request.httpBody=Data("{}".utf8);request.timeoutInterval=12
        session.dataTask(with:request){[weak self] data,response,error in
            let status=(response as? HTTPURLResponse)?.statusCode
            let body=data.flatMap{try? JSONSerialization.jsonObject(with:$0) as? [String:Any]}
            let message=body?["detail"] as? String ?? (status==200 ? "寻找指令已提交" : "寻找结果未知，请确认药盒响应后重试")
            DispatchQueue.main.async{guard let self else{return};self.finding=false;self.web.callAsyncJavaScript("window.tailFindState(false,message)",arguments:["message":message],in:nil,in:.page,completionHandler:nil);self.fetch()}
        }.resume()
    }
    func windowWillClose(_ notification:Notification){timer?.invalidate();dragTimer?.invalidate();session.invalidateAndCancel();web.configuration.userContentController.removeScriptMessageHandler(forName:"tail");NSApp.terminate(nil)}
}
let app=NSApplication.shared;let delegate=AppDelegate();app.setActivationPolicy(.accessory);app.delegate=delegate;app.run()
