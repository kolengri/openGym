package ch.duartesantos.opengym;

import android.content.Context;
import android.net.http.SslError;
import android.os.Handler;
import android.os.Looper;
import android.webkit.ConsoleMessage;
import android.webkit.CookieManager;
import android.webkit.SslErrorHandler;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

/** Official Connect/CAS browser renewal. No password, guessed refresh API or JavaScript bridge. */
final class GarminCloudRenewal {
    private static final String CONNECT = "https://connect.garmin.com/app/";
    private static final long TIMEOUT_MS = 45000;
    private static final Handler MAIN = new Handler(Looper.getMainLooper());
    private static final AtomicLong EPOCH = new AtomicLong();
    private static Job active; // Main-thread-owned; IO waits only on the bounded job's latch.

    static long lease() { return EPOCH.get(); }

    /** Revoke immediately, even while the serial IO executor is waiting for the browser. */
    static void cancelPending() {
        EPOCH.incrementAndGet();
        MAIN.post(() -> { if (active != null && active.epoch != EPOCH.get()) active.finish("cancelled"); });
    }

    static GarminCloudSession.Renewal forOperation(Context context, long epoch) {
        Context application = context.getApplicationContext();
        return new GarminCloudSession.Renewal() {
            @Override public GarminCloudSession.Credentials fetch(String previousToken) throws GarminCloudClient.Failure {
                return GarminCloudRenewal.fetch(application, epoch, previousToken);
            }
            @Override public void check() throws GarminCloudClient.Failure {
                if (epoch != EPOCH.get()) throw new GarminCloudClient.Failure("cancelled");
            }
        };
    }

    private static GarminCloudSession.Credentials fetch(Context context, long epoch, String previousToken)
        throws GarminCloudClient.Failure {
        if (Looper.myLooper() == Looper.getMainLooper()) throw new GarminCloudClient.Failure("auth_expired");
        if (epoch != EPOCH.get()) throw new GarminCloudClient.Failure("cancelled");
        Job job = new Job(context, epoch, previousToken);
        MAIN.post(job::start);
        try {
            if (!job.finished.await(TIMEOUT_MS + 1000, TimeUnit.MILLISECONDS)) job.finish("network_error");
        } catch (InterruptedException ignored) {
            Thread.currentThread().interrupt();
            job.finish("cancelled");
        }
        if (epoch != EPOCH.get()) throw new GarminCloudClient.Failure("cancelled");
        if (job.error != null) throw new GarminCloudClient.Failure(job.error);
        // flush() may block on disk I/O, so persist cookies on the serial IO thread.
        try { CookieManager.getInstance().flush(); }
        catch (Exception ignored) { throw new GarminCloudClient.Failure("storage_unavailable"); }
        String binding = new GarminHealthClient().accountBinding(job.token, job.csrf);
        if (epoch != EPOCH.get()) throw new GarminCloudClient.Failure("cancelled");
        return new GarminCloudSession.Credentials(job.token, job.csrf, binding);
    }

    private static final class Job {
        final Context context;
        final long epoch;
        final String previousToken;
        final CountDownLatch finished = new CountDownLatch(1);
        final AtomicBoolean done = new AtomicBoolean();
        volatile String error, token, csrf;
        WebView web;
        boolean signInPage;
        final Runnable deadline = () -> finish(signInPage ? "auth_required" : "network_error");
        final Runnable poll = new Runnable() {
            @Override public void run() {
                if (done.get()) return;
                capture();
                if (!done.get()) MAIN.postDelayed(this, 500);
            }
        };

        Job(Context context, long epoch, String previousToken) {
            this.context = context; this.epoch = epoch; this.previousToken = previousToken;
        }

        void start() {
            if (done.get()) return;
            if (epoch != EPOCH.get()) { finish("cancelled"); return; }
            if (active != null) { finish("cancelled"); return; }
            active = this;
            MAIN.postDelayed(deadline, TIMEOUT_MS);
            try {
                web = new WebView(context);
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
                CookieManager.getInstance().setAcceptThirdPartyCookies(web, false);
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
                        signInPage = false;
                        if (!GarminCloudClient.allowedLoginUrl(url)) { view.stopLoading(); finish("auth_required"); }
                    }
                    @Override public void onPageFinished(WebView view, String url) {
                        if (done.get()) return;
                        signInPage = GarminCloudClient.allowedLoginUrl(url)
                            && "sso.garmin.com".equalsIgnoreCase(android.net.Uri.parse(url).getHost());
                        capture();
                    }
                    @Override public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                        handler.cancel(); finish("network_error");
                    }
                    @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                        if (request.isForMainFrame()) finish("network_error");
                    }
                    @Override public void onReceivedHttpError(WebView view, WebResourceRequest request, WebResourceResponse response) {
                        if (request.isForMainFrame()) finish("network_error");
                    }
                });
                // Remove only the rejected/expired access cookie. CAS/SSO cookies choose the account;
                // the authoritative profile binding below must still match before native acceptance.
                expireAccessCookie(() -> {
                    if (done.get()) return;
                    if (epoch != EPOCH.get()) { finish("cancelled"); return; }
                    web.loadUrl(CONNECT);
                    MAIN.post(poll);
                });
            } catch (Exception ignored) { finish("network_error"); }
        }

        void capture() {
            if (done.get() || web == null || !GarminCloudClient.completedLoginUrl(web.getUrl())) return;
            if (epoch != EPOCH.get()) { finish("cancelled"); return; }
            String cookies = CookieManager.getInstance().getCookie(CONNECT);
            String candidate = GarminCloudClient.cookie(cookies, "JWT_WEB");
            String candidateCsrf = GarminCloudClient.cookie(cookies, "connect-csrf-token");
            if (!GarminCloudClient.validToken(candidate) || candidate.equals(previousToken)
                || !GarminCloudClient.validCsrf(candidateCsrf)) return;
            token = candidate; csrf = candidateCsrf;
            finish(null);
        }

        void finish(String failure) {
            if (!done.compareAndSet(false, true)) return;
            error = failure;
            MAIN.post(() -> {
                try {
                    MAIN.removeCallbacks(deadline);
                    MAIN.removeCallbacks(poll);
                    if (web != null) { web.stopLoading(); web.destroy(); }
                } finally {
                    web = null;
                    if (active == this) active = null;
                    finished.countDown();
                }
            });
        }
    }

    private static void expireAccessCookie(Runnable done) {
        CookieManager cookies = CookieManager.getInstance();
        String[] hosts = {"connect.garmin.com", "garmin.com"};
        String[] paths = {"/", "/app", "/app/", "/modern", "/modern/"};
        AtomicInteger remaining = new AtomicInteger(hosts.length * paths.length * 3);
        for (String host : hosts) for (String path : paths) {
            String value = "JWT_WEB=; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=" + path + "; Secure; HttpOnly";
            for (String domain : new String[]{"", "; Domain=" + host, "; Domain=.garmin.com"})
                cookies.setCookie("https://" + host + "/", value + domain, ignored -> {
                    if (remaining.decrementAndGet() == 0) done.run();
                });
        }
    }
}
