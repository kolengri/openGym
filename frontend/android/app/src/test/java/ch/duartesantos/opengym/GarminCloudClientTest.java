package ch.duartesantos.opengym;

import org.junit.Test;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Map;
import static org.junit.Assert.*;

public class GarminCloudClientTest {
    // A synthetic FIT container, not an account export or personal workout.
    static byte[] fit(int dataLength) {
        byte[] file = new byte[14 + dataLength + 2];
        file[0] = 14;
        file[1] = 0x20;
        for (int i = 0; i < 4; i++) file[4 + i] = (byte) (dataLength >>> (i * 8));
        file[8] = '.'; file[9] = 'F'; file[10] = 'I'; file[11] = 'T';
        int headerCrc = GarminCloudClient.crc(file, 12);
        file[12] = (byte) headerCrc; file[13] = (byte) (headerCrc >>> 8);
        int crc = GarminCloudClient.crc(file, file.length - 2);
        file[file.length - 2] = (byte) crc; file[file.length - 1] = (byte) (crc >>> 8);
        return file;
    }

    private void failure(String code, int status, String body) {
        assertEquals(code, assertThrows(GarminCloudClient.Failure.class, () -> GarminCloudClient.response(status, body)).code);
    }

    @Test public void acceptsFitContainerAndRejectsCorruptionTruncationAndSize() throws Exception {
        byte[] valid = fit(64);
        GarminCloudClient.validateFit(valid);
        byte[] corrupted = valid.clone(); corrupted[20] ^= 1;
        assertThrows(GarminCloudClient.Failure.class, () -> GarminCloudClient.validateFit(corrupted));
        assertThrows(GarminCloudClient.Failure.class, () -> GarminCloudClient.validateFit(Arrays.copyOf(valid, valid.length - 1)));
        byte[] wrongMagic = valid.clone(); wrongMagic[9] = 'X';
        assertThrows(GarminCloudClient.Failure.class, () -> GarminCloudClient.validateFit(wrongMagic));
        assertThrows(GarminCloudClient.Failure.class, () -> GarminCloudClient.validateFit(new byte[GarminCloudClient.MAX_FIT_BYTES + 1]));
        assertThrows(GarminCloudClient.Failure.class, () -> GarminCloudClient.validateFit(null));
        assertThrows(GarminCloudClient.Failure.class, () -> GarminCloudClient.validateFit(new byte[12]));
    }

    @Test public void validatesBase64WithoutRecursiveRegexAtMaximumPayload() throws Exception {
        String maximum = java.util.Base64.getEncoder().encodeToString(new byte[GarminCloudClient.MAX_FIT_BYTES]);
        GarminCloudClient.validateBase64(maximum);
        for (String invalid : new String[]{"", "a", "a===", "====", "AA=A", "AA\n=", "AA-_", maximum + "AAAA"})
            assertThrows(GarminCloudClient.Failure.class, () -> GarminCloudClient.validateBase64(invalid));
        GarminCloudClient.validateBase64("AA==");
        GarminCloudClient.validateBase64("AAA=");
    }

    @Test public void constructsOrdinaryUploadMultipartWithoutMobileImportPartHeaders() throws Exception {
        byte[] fit = fit(20);
        String multipart = new String(GarminCloudClient.multipart(fit, "test\r\n\"/file.FIT", "syntheticBoundary"), StandardCharsets.ISO_8859_1);
        assertEquals("https://connectapi.garmin.com/upload-service/upload", GarminCloudClient.UPLOAD_URL);
        assertTrue(multipart.startsWith("--syntheticBoundary\r\nContent-Disposition: form-data; name=\"file\"; filename=\"test____file.fit\"\r\n\r\n"));
        assertFalse(multipart.contains("Content-Type:"));
        assertTrue(multipart.endsWith("\r\n--syntheticBoundary--\r\n"));
        assertEquals("workout.fit", GarminCloudClient.filename(null));
        assertTrue(GarminCloudClient.filename("a".repeat(1024)).length() <= 104);
    }

    @Test public void usesOnlyVerifiedJwtFallbackHeaders() throws Exception {
        Map<String, String> headers = GarminCloudClient.headers("synthetic.payload.signature", null, "boundary");
        assertEquals("JWT_WEB=synthetic.payload.signature", headers.get("Cookie"));
        assertEquals("https://connect.garmin.com", headers.get("Origin"));
        assertEquals("https://connect.garmin.com/modern/", headers.get("Referer"));
        assertEquals("NT", headers.get("NK"));
        assertEquals("connectapi.garmin.com", headers.get("DI-Backend"));
        assertFalse(headers.containsKey("Authorization"));
        assertFalse(headers.containsKey("connect-csrf-token"));
        assertFalse(headers.containsValue("GCM-iOS-5.7.2.1"));
        assertEquals("csrf", GarminCloudClient.headers("synthetic.payload.signature", "csrf", "boundary").get("connect-csrf-token"));
        assertThrows(GarminCloudClient.Failure.class, () -> GarminCloudClient.headers("bad\r\nHeader: value", null, "boundary"));
        assertThrows(GarminCloudClient.Failure.class, () -> GarminCloudClient.headers("synthetic.payload.signature", "bad\r\nvalue", "boundary"));
    }

    @Test public void parsesOnlyExplicitSuccessAndReturnsReceiptFields() throws Exception {
        String body = "{\"detailedImportResult\":{\"successes\":[{\"internalId\":12345,\"private\":\"ignored\"}],\"failures\":[]},\"token\":\"never-return\"}";
        GarminCloudClient.Outcome result = GarminCloudClient.response(201, body);
        assertEquals("uploaded", result.status);
        assertEquals("12345", result.activityId);
        GarminCloudClient.Outcome duplicate = GarminCloudClient.response(409, "<html>private error</html>");
        assertEquals("duplicate", duplicate.status);
        assertNull(duplicate.activityId);
    }

    @Test public void distinguishesAuthenticationRejectionAndAmbiguousResponses() {
        failure("auth_required", 401, "private");
        failure("auth_required", 403, "private");
        failure("upload_failed", 400, "private");
        failure("upload_failed", 422, "private");
        failure("upload_failed", 200, "{\"detailedImportResult\":{\"successes\":[],\"failures\":[{}]}}");
        for (int status : new int[]{200, 202, 302, 429, 500, 503}) failure("unknown_result", status, "<html>private</html>");
        failure("unknown_result", 200, "{\"detailedImportResult\":{\"successes\":[{\"internalId\":\"private\"}],\"failures\":[]}}");
        failure("unknown_result", 200, "{\"detailedImportResult\":{\"successes\":[{\"internalId\":123}],\"failures\":[{}]}}");
        failure("unknown_result", 200, "x".repeat(GarminCloudClient.MAX_RESPONSE_BYTES + 1));
    }

    @Test public void restrictsLoginToExactHttpsGarminOrigins() {
        assertTrue(GarminCloudClient.allowedLoginUrl("https://sso.garmin.com/portal/sso/en-US/sign-in"));
        assertTrue(GarminCloudClient.completedLoginUrl("https://connect.garmin.com/app/activities"));
        assertTrue(GarminCloudClient.completedLoginUrl("https://connect.garmin.com/modern/"));
        assertFalse(GarminCloudClient.completedLoginUrl("https://sso.garmin.com/app/"));
        assertFalse(GarminCloudClient.completedLoginUrl("https://connect.garmin.com/application"));
        for (String invalid : new String[]{"http://connect.garmin.com/", "https://connect.garmin.com.evil.test/", "https://evil.test/connect.garmin.com/", "https://connect.garmin.com@evil.test/", "https://user@connect.garmin.com/", "https://connect.garmin.com:444/", "intent://connect.garmin.com/", "file:///tmp/login", "javascript:alert(1)"})
            assertFalse(invalid, GarminCloudClient.allowedLoginUrl(invalid));
    }

    @Test public void extractsOnlyNamedCookieWithoutExposingAWholeJar() {
        assertEquals("synthetic.payload.signature", GarminCloudClient.cookie("other=private; JWT_WEB=synthetic.payload.signature; extra=hidden", "JWT_WEB"));
        assertNull(GarminCloudClient.cookie("notJWT_WEB=private", "JWT_WEB"));
        assertFalse(GarminCloudClient.validToken("not-a-jwt"));
        assertFalse(GarminCloudClient.validToken("bad.payload.sig; extra=secret"));
    }
}
