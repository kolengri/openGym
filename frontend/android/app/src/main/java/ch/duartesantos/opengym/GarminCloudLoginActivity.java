package ch.duartesantos.opengym;

import android.app.Activity;
import android.content.Intent;
import java.lang.ref.WeakReference;
import android.graphics.Color;
import android.net.http.SslError;
import android.os.Bundle;
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
    static final String ERROR = "garminLoginError";
    private static WeakReference<GarminCloudLoginActivity> active = new WeakReference<>(null);
    private String nonce;
    private WebView web;
    private TextView title;
    private boolean saving, closing;
    private GarminCloudAuth.LoginAttempt attempt;
    private long loginLease;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
        nonce = getIntent().getStringExtra(NONCE);
        loginLease = GarminCloudRenewal.lease();
        GarminCloudLoginActivity previous = active.get();
        if (previous != null && previous != this) previous.dismiss();
        active = new WeakReference<>(this);
        setResult(RESULT_CANCELED, new Intent().putExtra(NONCE, nonce));
        if (!GarminCloudStore.validSession(nonce)) { closing = true; super.finish(); return; }
        attempt = new GarminCloudAuth.LoginAttempt(nonce);
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
                return captureTicket(request.getUrl().toString(), request.getMethod(), request.isForMainFrame())
                    || !GarminCloudClient.allowedLoginUrl(request.getUrl().toString());
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, String url) {
                return captureTicket(url, "GET", true) || !GarminCloudClient.allowedLoginUrl(url);
            }
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                if (captureTicket(request.getUrl().toString(), request.getMethod(), request.isForMainFrame())
                    || (request.isForMainFrame() && !GarminCloudClient.allowedLoginUrl(request.getUrl().toString())))
                    return new WebResourceResponse("text/plain", "UTF-8", new java.io.ByteArrayInputStream(new byte[0]));
                return null;
            }
            @Override public void onPageStarted(WebView view, String url, android.graphics.Bitmap icon) {
                if (!GarminCloudClient.allowedLoginUrl(url)) { view.stopLoading(); return; }
                title.setText("Garmin Connect · " + android.net.Uri.parse(url).getHost());
            }
            @Override public void onPageFinished(WebView view, String url) {
                // This callback runs after loading, so a ticket observed here may already be consumed.
                if (!saving && !closing && attempt.incompletePage(url))
                    finishResult("auth_incomplete");
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
        checkAuthorization(() -> clearGarminCookies(() -> {
            checkAuthorization(() -> {
                if (!closing && !isFinishing() && !isDestroyed() && web != null) web.loadUrl(GarminCloudAuth.SIGN_IN);
            });
        }));
    }

    /** Claim synchronously, block the service GET, then move native exchange onto serial IO. */
    private boolean captureTicket(String url, String method, boolean mainFrame) {
        if (!mainFrame || !"GET".equals(method) || GarminCloudAuth.serviceTicket(url) == null) return false;
        String ticket = attempt.claim(url, method, true);
        if (ticket != null) runOnUiThread(() -> exchangeTicket(ticket));
        // Also block duplicate navigation after another hook has already claimed this attempt.
        return true;
    }

    private void exchangeTicket(String ticket) {
        if (saving || closing || isFinishing() || isDestroyed() || !attempt.active()) return;
        saving = true;
        web.stopLoading();
        title.setText("Saving Garmin connection…");
        GarminCloudStore.IO.execute(() -> {
            String failure = null;
            try {
                GarminCloudAuth.completeLogin(GarminCloudStore.open(getApplicationContext()), attempt, ticket,
                    new GarminCloudAuth(), () -> GarminCloudRenewal.checkLease(loginLease));
            } catch (GarminCloudClient.Failure rejected) { failure = rejected.code; }
            catch (Exception ignored) { failure = "storage_unavailable"; }
            String error = failure;
            runOnUiThread(() -> {
                if (closing || isFinishing() || isDestroyed()) return;
                // Renewal uses the DI refresh grant. Do not retain a second browser login session.
                clearGarminCookies(() -> finishResult(error));
            });
        });
    }

    private void finishResult(String error) {
        if (closing || isFinishing() || isDestroyed()) return;
        closing = true;
        attempt.cancel();
        if (web != null) web.stopLoading();
        setResult(error == null ? RESULT_OK : RESULT_CANCELED,
            new Intent().putExtra(NONCE, nonce).putExtra(ERROR, error));
        finish();
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
                    clearGarminCookies(() -> finishResult(null));
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
        if (attempt != null) attempt.cancel();
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
        if (attempt != null) attempt.cancel();
        GarminCloudRenewal.cancelPending();
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
        if (attempt != null) attempt.cancel();
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
