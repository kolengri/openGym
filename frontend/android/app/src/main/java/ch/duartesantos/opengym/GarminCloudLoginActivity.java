package ch.duartesantos.opengym;

import android.app.Activity;
import android.content.Intent;
import java.lang.ref.WeakReference;
import android.graphics.Color;
import android.net.http.SslError;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.SslErrorHandler;
import android.webkit.WebChromeClient;
import android.webkit.ConsoleMessage;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebStorage;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;

/** Official Garmin pages in a plain WebView. It has no Capacitor bridge or JavaScript interface. */
public final class GarminCloudLoginActivity extends Activity {
    static final String NONCE = "garminLoginNonce";
    private static WeakReference<GarminCloudLoginActivity> active = new WeakReference<>(null);
    private String nonce;
    private WebView web;
    private TextView title;
    private boolean saving, closing;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final Runnable cookieCheck = new Runnable() {
        @Override public void run() {
            if (web == null || saving || closing || isFinishing() || isDestroyed()) return;
            captureSession(web.getUrl());
            if (!saving) main.postDelayed(this, 1000);
        }
    };

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
        nonce = getIntent().getStringExtra(NONCE);
        GarminCloudLoginActivity previous = active.get();
        if (previous != null && previous != this) previous.dismiss();
        active = new WeakReference<>(this);
        setResult(RESULT_CANCELED, new Intent().putExtra(NONCE, nonce));
        if (!GarminCloudStore.validSession(nonce)) { closing = true; super.finish(); return; }
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setBackgroundColor(Color.WHITE);
        ViewCompat.setOnApplyWindowInsetsListener(layout, (view, insets) -> {
            Insets bars = insets.getInsets(WindowInsetsCompat.Type.systemBars() | WindowInsetsCompat.Type.displayCutout() | WindowInsetsCompat.Type.ime());
            view.setPadding(bars.left, bars.top, bars.right, bars.bottom);
            return insets;
        });
        title = new TextView(this);
        title.setText("Garmin Connect · connect.garmin.com");
        title.setTextColor(Color.BLACK);
        title.setPadding(24, 20, 24, 12);
        layout.addView(title);
        Button cancel = new Button(this);
        cancel.setText("Cancel");
        cancel.setOnClickListener(view -> cancelLogin());
        layout.addView(cancel);
        web = new WebView(this);
        layout.addView(web, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));
        setContentView(layout);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setAllowFileAccessFromFileURLs(false);
        settings.setAllowUniversalAccessFromFileURLs(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setJavaScriptCanOpenWindowsAutomatically(false);
        settings.setSupportMultipleWindows(false);
        settings.setSaveFormData(false);
        CookieManager cookies = CookieManager.getInstance();
        cookies.setAcceptThirdPartyCookies(web, false);
        // Consume console messages without forwarding page content to application/device logs.
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onConsoleMessage(ConsoleMessage message) { return true; }
        });
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return !GarminCloudClient.allowedLoginUrl(request.getUrl().toString());
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, String url) {
                return !GarminCloudClient.allowedLoginUrl(url);
            }
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                if (request.isForMainFrame() && !GarminCloudClient.allowedLoginUrl(request.getUrl().toString()))
                    return new WebResourceResponse("text/plain", "UTF-8", new java.io.ByteArrayInputStream(new byte[0]));
                return null;
            }
            @Override public void onPageStarted(WebView view, String url, android.graphics.Bitmap icon) {
                if (!GarminCloudClient.allowedLoginUrl(url)) { view.stopLoading(); return; }
                title.setText("Garmin Connect · " + android.net.Uri.parse(url).getHost());
            }
            @Override public void onPageFinished(WebView view, String url) {
                captureSession(url);
                main.removeCallbacks(cookieCheck);
                if (!saving && GarminCloudClient.allowedLoginUrl(url)) main.postDelayed(cookieCheck, 1000);
            }
            @Override public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                handler.cancel();
                title.setText("Garmin sign-in could not establish a secure connection. Close and try again.");
            }
            @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) title.setText("Garmin sign-in could not load. Close and try again.");
            }
        });
        // A fresh official login prevents a previous WebView session selecting another account silently.
        clearGarminCookies(() -> {
            checkAuthorization(() -> {
                if (!closing && !isFinishing() && !isDestroyed() && web != null) web.loadUrl("https://connect.garmin.com/app/");
            });
        });
    }

    private void captureSession(String url) {
        if (saving || closing || isDestroyed() || !GarminCloudClient.completedLoginUrl(url)
            || web == null || !GarminCloudClient.completedLoginUrl(web.getUrl())) return;
        String cookies = CookieManager.getInstance().getCookie("https://connect.garmin.com/app/");
        String token = GarminCloudClient.cookie(cookies, "JWT_WEB");
        String csrf = GarminCloudClient.cookie(cookies, "connect-csrf-token");
        if (!GarminCloudClient.validToken(token) || !GarminCloudClient.validCsrf(csrf)) return;
        saving = true;
        web.stopLoading();
        title.setText("Saving Garmin connection…");
        GarminCloudStore.IO.execute(() -> {
            boolean saved;
            try { GarminCloudStore.saveLogin(getApplicationContext(), nonce, token, csrf); saved = true; }
            catch (Exception ignored) { saved = false; }
            boolean success = saved;
            runOnUiThread(() -> {
                if (closing || isFinishing() || isDestroyed()) return;
                clearGarminCookies(() -> {
                    if (closing || isFinishing() || isDestroyed()) return;
                    closing = true;
                    if (success) setResult(RESULT_OK, new Intent().putExtra(NONCE, nonce));
                    finish();
                });
            });
        });
    }

    private void checkAuthorization(Runnable pending) {
        GarminCloudStore.IO.execute(() -> {
            boolean allowed = false, completed = false;
            try {
                GarminCloudStore store = GarminCloudStore.open(getApplicationContext());
                allowed = store.pendingLogin(nonce);
                completed = store.loginResultMatches(nonce);
            } catch (Exception ignored) { /* Unreadable storage cannot authorize login. */ }
            boolean valid = allowed, saved = completed;
            runOnUiThread(() -> {
                if (closing || isFinishing() || isDestroyed()) return;
                if (saved) {
                    closing = true;
                    setResult(RESULT_OK, new Intent().putExtra(NONCE, nonce));
                    finish();
                } else if (!valid) dismiss();
                else pending.run();
            });
        });
    }

    @Override protected void onResume() {
        super.onResume();
        if (nonce != null) checkAuthorization(() -> {});
    }

    private void dismiss() {
        closing = true;
        if (web != null) web.stopLoading();
        super.finish();
    }

    static void dismissCancelled(String nonce) {
        GarminCloudLoginActivity activity = active.get();
        if (activity != null && nonce != null && nonce.equals(activity.nonce)) activity.dismiss();
    }

    private void cancelLogin() {
        if (closing) return;
        closing = true;
        if (web != null) web.stopLoading();
        GarminCloudStore.IO.execute(() -> {
            try { GarminCloudStore.open(getApplicationContext()).cancelLogin(nonce); }
            catch (Exception ignored) { /* Preserve an unreadable archive. */ }
            runOnUiThread(() -> clearGarminCookies(this::finish));
        });
    }

    @Override public void onBackPressed() { cancelLogin(); }

    @Override public void finish() {
        if (!closing) { cancelLogin(); return; }
        super.finish();
    }

    @Override protected void onDestroy() {
        main.removeCallbacks(cookieCheck);
        if (active.get() == this) active.clear();
        if (web != null) {
            ((ViewGroup) web.getParent()).removeView(web);
            web.stopLoading();
            web.destroy();
            web = null;
        }
        super.onDestroy();
    }

    /** Expire this app's Garmin cookies only; never clear the shared Capacitor cookie jar. */
    static void clearGarminCookies(Runnable done) {
        CookieManager manager = CookieManager.getInstance();
        WebStorage webStorage = WebStorage.getInstance();
        String[] hosts = {"connect.garmin.com", "sso.garmin.com", "garmin.com"};
        String[] paths = {"/", "/app", "/app/", "/modern", "/modern/", "/sso", "/sso/", "/portal/sso", "/portal/sso/"};
        List<String[]> expired = new ArrayList<>();
        for (String host : hosts) {
            webStorage.deleteOrigin("https://" + host);
            Set<String> names = new LinkedHashSet<>();
            names.add("JWT_WEB");
            names.add("connect-csrf-token");
            for (String path : paths) {
                String header = manager.getCookie("https://" + host + path);
                if (header != null) for (String cookie : header.split(";")) {
                    int equals = cookie.indexOf('=');
                    String name = equals > 0 ? cookie.substring(0, equals).trim() : "";
                    if (name.matches("[A-Za-z0-9_!#$%&'*+.^`|~-]{1,128}")) names.add(name);
                }
            }
            for (String name : names) for (String path : paths) {
                String value = name + "=; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=" + path + "; Secure; HttpOnly";
                String origin = "https://" + host + "/";
                expired.add(new String[]{origin, value});
                expired.add(new String[]{origin, value + "; Domain=" + host});
                expired.add(new String[]{origin, value + "; Domain=.garmin.com"});
            }
        }
        AtomicInteger remaining = new AtomicInteger(expired.size());
        for (String[] cookie : expired) manager.setCookie(cookie[0], cookie[1], ignored -> {
            if (remaining.decrementAndGet() == 0) {
                manager.flush();
                done.run();
            }
        });
    }
}
