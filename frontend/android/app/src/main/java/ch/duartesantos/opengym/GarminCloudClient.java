package ch.duartesantos.opengym;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URI;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import javax.net.ssl.HttpsURLConnection;

/** The ordinary Connect upload endpoint; deliberately not the mobile import endpoint. */
final class GarminCloudClient {
    static final String UPLOAD_URL = "https://connectapi.garmin.com/upload-service/upload";
    static final int MAX_FIT_BYTES = 2 * 1024 * 1024;
    static final int MAX_RESPONSE_BYTES = 128 * 1024;
    static final ScheduledExecutorService DEADLINES = Executors.newSingleThreadScheduledExecutor();

    static final class Failure extends Exception {
        final String code;
        Failure(String code) { super(code); this.code = code; }
    }

    static final class Outcome {
        final String status, activityId;
        Outcome(String status, String activityId) { this.status = status; this.activityId = activityId; }
    }

    static boolean allowedLoginUrl(String value) {
        try {
            URI uri = new URI(value);
            return "https".equalsIgnoreCase(uri.getScheme()) && uri.getRawUserInfo() == null
                && (uri.getPort() == -1 || uri.getPort() == 443)
                && ("connect.garmin.com".equalsIgnoreCase(uri.getHost())
                    || "sso.garmin.com".equalsIgnoreCase(uri.getHost()));
        } catch (Exception e) { return false; }
    }

    static boolean completedLoginUrl(String value) {
        if (!allowedLoginUrl(value)) return false;
        URI uri = URI.create(value);
        String path = uri.getPath();
        return "connect.garmin.com".equalsIgnoreCase(uri.getHost()) && path != null
            && (path.equals("/app") || path.startsWith("/app/")
                || path.equals("/modern") || path.startsWith("/modern/"));
    }

    static String cookie(String header, String name) {
        if (header == null || header.length() > 64 * 1024) return null;
        for (String entry : header.split(";")) {
            String value = entry.trim();
            if (value.startsWith(name + "=")) return value.substring(name.length() + 1);
        }
        return null;
    }

    static boolean validToken(String token) {
        return token != null && token.length() <= 16384
            && token.matches("[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+");
    }

    static boolean validCsrf(String csrf) {
        return csrf == null || (csrf.length() <= 512 && csrf.matches("[A-Za-z0-9._~-]+"));
    }

    static void validateBase64(String value) throws Failure {
        if (value == null || value.length() == 0 || value.length() > ((MAX_FIT_BYTES + 2) / 3) * 4
            || value.length() % 4 != 0)
            throw new Failure("upload_failed");
        int padding = value.endsWith("==") ? 2 : value.endsWith("=") ? 1 : 0;
        for (int i = 0; i < value.length() - padding; i++) {
            char c = value.charAt(i);
            if (!(c >= 'A' && c <= 'Z') && !(c >= 'a' && c <= 'z') && !(c >= '0' && c <= '9') && c != '+' && c != '/')
                throw new Failure("upload_failed");
        }
    }

    static void validateFit(byte[] fit) throws Failure {
        if (fit == null || fit.length < 15 || fit.length > MAX_FIT_BYTES) throw new Failure("upload_failed");
        int header = fit[0] & 255;
        long data = (fit[4] & 255L) | ((fit[5] & 255L) << 8)
            | ((fit[6] & 255L) << 16) | ((fit[7] & 255L) << 24);
        if ((header != 12 && header != 14) || data < 1 || header + data + 2 != fit.length
            || fit[8] != '.' || fit[9] != 'F' || fit[10] != 'I' || fit[11] != 'T'
            || (header == 14 && (fit[12] != 0 || fit[13] != 0) && crc(fit, 14) != 0)
            || crc(fit, fit.length) != 0) throw new Failure("upload_failed");
    }

    static int crc(byte[] data, int length) {
        int crc = 0;
        for (int i = 0; i < length; i++) {
            crc ^= data[i] & 255;
            for (int bit = 0; bit < 8; bit++) crc = (crc & 1) != 0 ? (crc >>> 1) ^ 0xa001 : crc >>> 1;
        }
        return crc;
    }

    static String sha256(byte[] value) throws Exception {
        StringBuilder hex = new StringBuilder();
        for (byte b : MessageDigest.getInstance("SHA-256").digest(value))
            hex.append(Character.forDigit((b >>> 4) & 15, 16)).append(Character.forDigit(b & 15, 16));
        return hex.toString();
    }

    static String filename(String input) {
        String name = input == null ? "workout" : input;
        if (name.length() > 256) name = name.substring(0, 256);
        if (name.toLowerCase(java.util.Locale.ROOT).endsWith(".fit")) name = name.substring(0, name.length() - 4);
        name = name.replaceAll("[^A-Za-z0-9_-]", "_");
        if (name.length() > 100) name = name.substring(0, 100);
        if (name.isEmpty()) name = "workout";
        return name + ".fit";
    }

    static Map<String, String> headers(String token, String csrf, String boundary) throws Failure {
        Map<String, String> headers = authHeaders(token, csrf);
        headers.put("Content-Type", "multipart/form-data; boundary=" + boundary);
        return headers;
    }

    static Map<String, String> authHeaders(String token, String csrf) throws Failure {
        if (!validToken(token) || !validCsrf(csrf)) throw new Failure("auth_required");
        Map<String, String> headers = new LinkedHashMap<>();
        headers.put("Accept", "application/json");
        headers.put("NK", "NT");
        headers.put("Origin", "https://connect.garmin.com");
        headers.put("Referer", "https://connect.garmin.com/modern/");
        headers.put("DI-Backend", "connectapi.garmin.com");
        headers.put("Cookie", "JWT_WEB=" + token);
        if (csrf != null) headers.put("connect-csrf-token", csrf);
        return headers;
    }

    static byte[] multipart(byte[] fit, String filename, String boundary) throws Exception {
        ByteArrayOutputStream body = new ByteArrayOutputStream();
        body.write(("--" + boundary + "\r\nContent-Disposition: form-data; name=\"file\"; filename=\""
            + filename(filename) + "\"\r\n\r\n").getBytes(StandardCharsets.US_ASCII));
        body.write(fit);
        body.write(("\r\n--" + boundary + "--\r\n").getBytes(StandardCharsets.US_ASCII));
        return body.toByteArray();
    }

    static Outcome response(int status, String body) throws Failure {
        if (status == 401 || status == 403) throw new Failure("auth_required");
        if (status == 409) return new Outcome("duplicate", null);
        if (status == 400 || status == 404 || status == 413 || status == 415 || status == 422)
            throw new Failure("upload_failed");
        if (status < 200 || status >= 300 || body == null || body.length() > MAX_RESPONSE_BYTES)
            throw new Failure("unknown_result");
        try {
            JSONObject result = new JSONObject(body).getJSONObject("detailedImportResult");
            JSONArray successes = result.optJSONArray("successes"), failures = result.optJSONArray("failures");
            if (successes != null && successes.length() == 1 && failures != null && failures.length() == 0) {
                String id = successes.getJSONObject(0).optString("internalId", "");
                if (id.matches("[1-9][0-9]{0,19}")) return new Outcome("uploaded", id);
            }
            if (successes != null && successes.length() == 0 && failures != null && failures.length() > 0)
                throw new Failure("upload_failed");
        } catch (Failure e) { throw e; }
        catch (Exception ignored) { /* Never expose the service response or its parse exception. */ }
        throw new Failure("unknown_result");
    }

    Outcome upload(byte[] fit, String filename, String token, String csrf) throws Failure {
        HttpsURLConnection connection = null;
        ScheduledFuture<?> deadline = null;
        boolean mayHaveSent = false;
        try {
            String boundary = "openGym" + UUID.randomUUID().toString().replace("-", "");
            byte[] body = multipart(fit, filename, boundary);
            Map<String, String> headers = headers(token, csrf, boundary);
            connection = (HttpsURLConnection) new URL(UPLOAD_URL).openConnection();
            HttpsURLConnection request = connection;
            deadline = DEADLINES.schedule(request::disconnect, 60, TimeUnit.SECONDS);
            connection.setRequestMethod("POST");
            connection.setInstanceFollowRedirects(false);
            connection.setConnectTimeout(15000);
            connection.setReadTimeout(30000);
            connection.setUseCaches(false);
            connection.setDoOutput(true);
            connection.setFixedLengthStreamingMode(body.length);
            for (Map.Entry<String, String> header : headers.entrySet())
                connection.setRequestProperty(header.getKey(), header.getValue());
            connection.connect();
            mayHaveSent = true;
            try (OutputStream out = connection.getOutputStream()) { out.write(body); }
            int status = connection.getResponseCode();
            // These statuses have an unambiguous meaning without consuming a possibly huge HTML body.
            if (status < 200 || status >= 300) return response(status, null);
            try (InputStream in = connection.getInputStream(); ByteArrayOutputStream bytes = new ByteArrayOutputStream()) {
                byte[] chunk = new byte[4096];
                int count;
                while ((count = in.read(chunk)) != -1) {
                    if (bytes.size() + count > MAX_RESPONSE_BYTES) throw new Failure("unknown_result");
                    bytes.write(chunk, 0, count);
                }
                return response(status, bytes.toString(StandardCharsets.UTF_8.name()));
            }
        } catch (Failure e) { throw e; }
        catch (Exception ignored) { throw new Failure(mayHaveSent ? "unknown_result" : "network_error"); }
        finally {
            if (deadline != null) deadline.cancel(false);
            if (connection != null) connection.disconnect();
        }
    }
}
