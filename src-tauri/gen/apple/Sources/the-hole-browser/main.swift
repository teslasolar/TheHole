import SwiftUI
import Tauri
import WebKit

@main
struct TheHoleBrowserApp: App {
    var body: some Scene {
        WindowGroup {
            TauriWebView()
                .ignoresSafeArea()
        }
    }
}

struct TauriWebView: UIViewRepresentable {
    func makeUIView(context: Context) -> WKWebView {
        let webView = Tauri.createWebView()
        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}
}
