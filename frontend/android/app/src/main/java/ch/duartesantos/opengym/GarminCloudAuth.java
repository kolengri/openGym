package ch.duartesantos.opengym;

import org.json.JSONObject;
import org.json.JSONTokener;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URI;
import java.net.URL;
import java.net.URLDecoder;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import javax.net.ssl.HttpsURLConnection;

/** CAS service-ticket exchange and refresh. All traffic is native and confined to Garmin DI. */
final class GarminCloudAuth {
    static final String SERVICE = "https://connect.garmin.com/app";
    static final String SIGN_IN = "https://sso.garmin.com/portal/sso/en-US/sign-in?clientId=GarminConnect&service=https%3A%2F%2Fconnect.garmin.com%2Fapp";
    static final String TOKEN_URL = "https://diauth.garmin.com/di-oauth2-service/oauth/token";
    static final String CLIENT_ID = "GARMIN_CONNECT_MOBILE_ANDROID_DI_2025Q2";
    static final String SERVICE_GRANT = "https://connectapi.garmin.com/di-oauth2-service/oauth/grant/service_ticket";
    private static final int MAX_BODY = 64 * 1024;

    /** Shared by both navigation hooks, including shouldInterceptRequest's background thread. */
    static final class LoginAttempt {
        final String nonce;
        private final AtomicBoolean claimed = new AtomicBoolean();
        private final AtomicBoolean cancelled = new AtomicBoolean();
        LoginAttempt(String nonce) {
            if (!GarminCloudStore.validSession(nonce)) throw new IllegalArgumentException("Invalid login attempt");
            this.nonce = nonce;
        }
        String claim(String url, String method, boolean mainFrame) {
            if (cancelled.get() || !mainFrame || !"GET".equals(method)) return null;
            String ticket = serviceTicket(url);
            return ticket != null && claimed.compareAndSet(false, true) && !cancelled.get() ? ticket : null;
        }
        void cancel() { cancelled.set(true); }
        boolean active() { return !cancelled.get(); }
        boolean claimed() { return claimed.get(); }
        boolean incompletePage(String url) { return active() && !claimed() && GarminCloudClient.completedLoginUrl(url); }
    }

    /** Exactly the service used to issue this attempt: /app and /app/ are not interchangeable. */
    static String serviceTicket(String value) {
        try {
            if (value == null || value.length() > 8192) return null;
            URI uri = new URI(value);
            if (!SERVICE.equals(new URI(uri.getScheme(), uri.getRawAuthority(), uri.getRawPath(), null, null).toString())
                || uri.getRawUserInfo() != null || uri.getPort() != -1 || uri.getRawFragment() != null) return null;
            String query = uri.getRawQuery();
            if (query == null) return null;
            String ticket = null;
            for (String entry : query.split("&", -1)) {
                int equals = entry.indexOf('=');
                if (equals < 0 || !"ticket".equals(URLDecoder.decode(entry.substring(0, equals), "UTF-8")) || ticket != null) return null;
                ticket = URLDecoder.decode(entry.substring(equals + 1), "UTF-8");
            }
            return validTicket(ticket) ? ticket : null;
        } catch (Exception ignored) { return null; }
    }

    static boolean validTicket(String value) {
        return value != null && value.length() <= 4096 && value.matches("ST-[A-Za-z0-9._~-]+");
    }
    static boolean validRefresh(String value) {
        if (value == null || value.isEmpty() || value.length() > 16384) return false;
        for (int i = 0; i < value.length(); i++) if (value.charAt(i) <= 32 || value.charAt(i) >= 127) return false;
        return true;
    }
    static boolean validClient(String value) {
        return CLIENT_ID.equals(value) || "GARMIN_CONNECT_MOBILE_ANDROID_DI_2024Q4".equals(value)
            || "GARMIN_CONNECT_MOBILE_ANDROID_DI".equals(value) || "GARMIN_CONNECT_MOBILE_IOS_DI".equals(value);
    }

    static final class Response {
        final int status;
        final String body;
        Response(int status, String body) { this.status = status; this.body = body; }
    }
    interface Transport { Response post(Map<String, String> headers, String body) throws GarminCloudClient.Failure; }
    private final Transport transport;
    private final java.util.function.LongSupplier now;
    private final java.util.function.Function<String, byte[]> decode;
    private final java.util.function.Function<byte[], String> basicEncoder;
    GarminCloudAuth() {
        this(new Http(), System::currentTimeMillis, value -> android.util.Base64.decode(value,
            android.util.Base64.URL_SAFE | android.util.Base64.NO_PADDING | android.util.Base64.NO_WRAP),
            value -> android.util.Base64.encodeToString(value, android.util.Base64.NO_WRAP));
    }
    GarminCloudAuth(Transport transport, java.util.function.LongSupplier now, java.util.function.Function<String, byte[]> decode,
                    java.util.function.Function<byte[], String> basicEncoder) {
        this.transport = transport; this.now = now; this.decode = decode; this.basicEncoder = basicEncoder;
    }

    /** Production orchestration seam: cancellation before/after HTTP and durable nonce recheck. */
    static void completeLogin(GarminCloudStore store, LoginAttempt attempt, String ticket, GarminCloudAuth auth,
                              GarminCloudClient.SessionProbe check) throws Exception {
        check.check();
        if (!attempt.active()) throw new GarminCloudClient.Failure("cancelled");
        store.reload();
        if (!store.pendingLogin(attempt.nonce)) throw new GarminCloudClient.Failure("cancelled");
        GarminCloudSession.Credentials credentials = auth.exchange(ticket, SERVICE);
        check.check();
        if (!attempt.active()) throw new GarminCloudClient.Failure("cancelled");
        store.finishLogin(attempt.nonce, credentials);
    }

    GarminCloudSession.Credentials exchange(String ticket, String service) throws GarminCloudClient.Failure {
        if (!validTicket(ticket) || !SERVICE.equals(service)) throw new GarminCloudClient.Failure("auth_exchange_failed");
        // A CAS ticket may be single-use. Do not guess alternate services or replay it across clients.
        return request(CLIENT_ID, "grant_type=" + encode(SERVICE_GRANT) + "&client_id=" + encode(CLIENT_ID)
            + "&service_ticket=" + encode(ticket) + "&service_url=" + encode(service), null);
    }

    GarminCloudSession.Credentials refresh(GarminCloudSession.Credentials previous) throws GarminCloudClient.Failure {
        if (!validRefresh(previous.refreshToken) || !validClient(previous.clientId)) throw new GarminCloudClient.Failure("auth_required");
        return request(previous.clientId, "grant_type=refresh_token&client_id=" + encode(previous.clientId)
            + "&refresh_token=" + encode(previous.refreshToken), previous.refreshToken);
    }

    private GarminCloudSession.Credentials request(String clientId, String body, String previousRefresh) throws GarminCloudClient.Failure {
        Map<String, String> headers = GarminCloudClient.nativeHeaders();
        headers.put("Authorization", "Basic " + basicEncoder.apply((clientId + ":").getBytes(StandardCharsets.UTF_8)));
        headers.put("Content-Type", "application/x-www-form-urlencoded");
        headers.put("Cache-Control", "no-cache");
        Response response = transport.post(headers, body);
        if (response.status == 429) throw new GarminCloudClient.Failure("rate_limited");
        if (response.status >= 500 || response.status < 200 || (response.status >= 300 && response.status < 400))
            throw new GarminCloudClient.Failure("network_error");
        JSONObject data = null;
        try {
            if (response.body != null && response.body.getBytes(StandardCharsets.UTF_8).length <= MAX_BODY) {
                GarminHealthClient.preflight(response.body);
                JSONTokener reader = new JSONTokener(response.body);
                Object parsed = reader.nextValue();
                if (parsed instanceof JSONObject && reader.nextClean() == 0) data = (JSONObject) parsed;
            }
        } catch (Exception ignored) { /* Never expose token response text or parser diagnostics. */ }
        if (response.status >= 400) {
            String error = data == null ? "" : data.optString("error", "");
            boolean rejectedGrant = "invalid_grant".equals(error) || "invalid_token".equals(error) || "expired_token".equals(error);
            if (previousRefresh != null && (rejectedGrant || (response.status == 401 && !"invalid_client".equals(error))))
                throw new GarminCloudClient.Failure("auth_required");
            throw new GarminCloudClient.Failure("auth_exchange_failed");
        }
        try {
            if (data == null || !(data.opt("access_token") instanceof String)) throw new Exception();
            String token = data.getString("access_token");
            Object refreshValue = data.opt("refresh_token");
            String refresh = refreshValue == null ? previousRefresh : refreshValue instanceof String ? (String) refreshValue : null;
            if (!GarminCloudClient.validToken(token) || !validRefresh(refresh)) throw new Exception();
            if (data.has("token_type") && !"Bearer".equalsIgnoreCase(data.getString("token_type"))) throw new Exception();
            long expires;
            if (data.has("expires_in")) {
                Object seconds = data.get("expires_in");
                if (!(seconds instanceof Number) || !seconds.toString().matches("[1-9][0-9]*")) throw new Exception();
                expires = Math.addExact(now.getAsLong(), Math.multiplyExact(((Number) seconds).longValue(), 1000L));
            } else {
                byte[] payload = decode.apply(token.split("\\.")[1]);
                if (payload == null || payload.length > 8192) throw new Exception();
                Object seconds = new JSONObject(new String(payload, StandardCharsets.UTF_8)).opt("exp");
                if (!(seconds instanceof Number) || !seconds.toString().matches("[1-9][0-9]*")) throw new Exception();
                expires = Math.multiplyExact(((Number) seconds).longValue(), 1000L);
            }
            if (expires <= now.getAsLong()) throw new Exception();
            return new GarminCloudSession.Credentials(token, refresh, clientId, expires);
        } catch (Exception ignored) { throw new GarminCloudClient.Failure("auth_exchange_failed"); }
    }

    private static String encode(String value) {
        try { return URLEncoder.encode(value, "UTF-8"); }
        catch (Exception impossible) { throw new IllegalStateException("UTF-8 unavailable"); }
    }

    static final class Http implements Transport {
        @Override public Response post(Map<String, String> headers, String body) throws GarminCloudClient.Failure {
            HttpsURLConnection connection = null;
            ScheduledFuture<?> deadline = null;
            try {
                byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
                connection = (HttpsURLConnection) new URL(TOKEN_URL).openConnection();
                HttpsURLConnection request = connection;
                deadline = GarminCloudClient.DEADLINES.schedule(request::disconnect, 45, TimeUnit.SECONDS);
                connection.setRequestMethod("POST");
                connection.setInstanceFollowRedirects(false);
                connection.setConnectTimeout(15000);
                connection.setReadTimeout(30000);
                connection.setUseCaches(false);
                connection.setDoOutput(true);
                connection.setFixedLengthStreamingMode(bytes.length);
                for (Map.Entry<String, String> header : headers.entrySet()) connection.setRequestProperty(header.getKey(), header.getValue());
                try (OutputStream out = connection.getOutputStream()) { out.write(bytes); }
                int status = connection.getResponseCode();
                if (status == 429 || status >= 500 || (status >= 300 && status < 400)) return new Response(status, null);
                InputStream source = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
                if (source == null) return new Response(status, null);
                try (InputStream in = source; ByteArrayOutputStream response = new ByteArrayOutputStream()) {
                    byte[] chunk = new byte[4096];
                    int count;
                    while ((count = in.read(chunk)) != -1) {
                        if (response.size() + count > MAX_BODY) throw new GarminCloudClient.Failure("auth_exchange_failed");
                        response.write(chunk, 0, count);
                    }
                    return new Response(status, response.toString(StandardCharsets.UTF_8.name()));
                }
            } catch (GarminCloudClient.Failure failure) { throw failure; }
            catch (Exception ignored) { throw new GarminCloudClient.Failure("network_error"); }
            finally {
                if (deadline != null) deadline.cancel(false);
                if (connection != null) connection.disconnect();
            }
        }
    }
}
