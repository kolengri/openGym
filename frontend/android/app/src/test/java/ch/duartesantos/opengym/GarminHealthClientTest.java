package ch.duartesantos.opengym;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import static org.junit.Assert.*;

/** Offline fixtures only: Transport is injected, and no account/network calls are made. */
public class GarminHealthClientTest {
    private static final String TOKEN = "synthetic.payload.signature";
    private static final String DAY = "2026-01-02";
    static final class Fixture implements GarminHealthClient.Transport {
        final List<String> urls = new ArrayList<>();
        int status = 200;
        String body = "{\"reading\":42}";
        String profile = "{\"displayName\":\"test/name?x#y\",\"email\":\"PRIVATE\",\"token\":\"PRIVATE\"}";
        @Override public GarminHealthClient.Response get(String url, String token, String csrf) {
            assertEquals(TOKEN, token);
            assertTrue(GarminHealthClient.allowedUrl(url));
            urls.add(url);
            return new GarminHealthClient.Response(status, url.equals(GarminHealthClient.PROFILE_URL) ? profile : body);
        }
    }
    private GarminCloudStore connected() throws Exception {
        GarminCloudStore store = new GarminCloudStore(new GarminCloudStoreTest.Disk());
        store.login(TOKEN, null);
        return store;
    }
    private void failure(String code, int status, String body) {
        assertEquals(code, assertThrows(GarminCloudClient.Failure.class,
            () -> GarminHealthClient.payload(new GarminHealthClient.Response(status, body))).code);
    }
    private String path(String id) throws Exception { return GarminHealthClient.endpoint(id, DAY, "2026-01-03", "synthetic"); }

    @Test public void staticCatalogIsUniqueAndContainsSupportedHealthFamilies() throws Exception {
        JSONArray catalog = GarminHealthClient.catalog();
        Set<String> ids = new HashSet<>();
        for (int i = 0; i < catalog.length(); i++) {
            JSONObject entry = catalog.getJSONObject(i);
            assertEquals(2, entry.length());
            assertTrue(entry.getString("label").length() > 0);
            assertTrue(ids.add(entry.getString("id")));
            assertTrue(GarminHealthClient.allowedUrl(path(entry.getString("id"))));
        }
        assertTrue(ids.containsAll(List.of("daily_summary", "weight", "sleep", "naps", "heart_rate", "resting_heart_rate",
            "hrv", "stress", "body_battery", "spo2", "respiration", "hydration", "intensity_minutes", "steps", "floors",
            "training_readiness", "training_status", "fitness_age", "max_metrics", "endurance_score", "hill_score",
            "blood_pressure", "health_snapshot", "ecg", "nutrition", "menstrual_day", "glucose")));
        assertFalse(ids.contains("skin_temperature")); // No separate endpoint exists in the installed source.
        assertFalse(ids.stream().anyMatch(id -> id.contains("weekly") || id.contains("monthly") || id.contains("download")));
    }

    @Test public void endpointsUseVerifiedDayQueriesAndNoRawEcgOrActivityDownloads() throws Exception {
        assertEquals("https://connectapi.garmin.com/weight-service/weight/dayview/2026-01-02?includeAll=true", path("weight"));
        assertEquals("https://connectapi.garmin.com/sleep-service/sleep/dailySleepData?date=2026-01-02&nonSleepBufferMinutes=60", path("sleep"));
        assertEquals("https://connectapi.garmin.com/bloodpressure-service/bloodpressure/dayview/2026-01-02", path("blood_pressure"));
        assertEquals("https://ghs.garmin.com/ghs/ecg/v1/ecg/daily?firstDay=2026-01-02&lastDay=2026-01-02", path("ecg"));
        assertEquals("https://connectapi.garmin.com/wellnessactivity-service/activity/summary/2026-01-02", path("health_snapshot"));
        assertEquals("https://connectapi.garmin.com/periodichealth-service/menstrualcycle/dayview/2026-01-02?todayDate=2026-01-03", path("menstrual_day"));
        assertThrows(GarminCloudClient.Failure.class, () -> path("https://evil.test"));
        assertThrows(GarminCloudClient.Failure.class, () -> path("../upload-service/upload"));
    }

    @Test public void validatesRealIsoDatesIncludingLeapDaysAndHistoryBoundaries() throws Exception {
        for (String date : new String[]{"2000-01-01", "2024-02-29", "2026-01-04"})
            GarminHealthClient.validateDate(date, "2026-01-03");
        for (String date : new String[]{"1999-12-31", "2026-01-05", "2025-02-29", "2024-02-30", "2026-00-12", "2026-13-01",
            "2026-1-02", "2026-01-02Z", "2026-01-02?x=y", "", "2026-01-02\n", "0000-01-01"}) {
            assertEquals("invalid_date", assertThrows(GarminCloudClient.Failure.class,
                () -> GarminHealthClient.validateDate(date, "2026-01-03")).code);
        }
        assertThrows(GarminCloudClient.Failure.class, () -> GarminHealthClient.validateDate(null, "2026-01-03"));
    }

    @Test public void bindsEveryReadToExactActiveSessionBeforeAnyTransport() throws Exception {
        Fixture fixture = new Fixture();
        GarminHealthClient client = new GarminHealthClient(fixture);
        GarminCloudStore store = connected();
        String old = store.sessionId();
        store.login(TOKEN, null);
        assertEquals("auth_required", assertThrows(GarminCloudClient.Failure.class,
            () -> client.read(store, old, DAY, "weight")).code);
        assertThrows(GarminCloudClient.Failure.class, () -> client.read(store, null, DAY, "weight"));
        store.disconnect();
        assertThrows(GarminCloudClient.Failure.class, () -> client.read(store, old, DAY, "weight"));
        assertTrue(fixture.urls.isEmpty());
    }

    @Test public void oneMetricGetPerCallAndNoUnnecessaryProfileRead() throws Exception {
        Fixture fixture = new Fixture();
        GarminCloudStore store = connected();
        JSONObject result = new GarminHealthClient(fixture).read(store, store.sessionId(), DAY, "weight");
        assertEquals(1, fixture.urls.size());
        assertEquals(path("weight"), fixture.urls.get(0));
        assertEquals("weight", result.getString("metric"));
        assertEquals(DAY, result.getString("date"));
        assertEquals("available", result.getString("status"));
        assertEquals(42, result.getJSONObject("data").getInt("reading"));
    }

    @Test public void profileOnlyCachesEncodedDisplayNameInActiveNativeSession() throws Exception {
        Fixture fixture = new Fixture();
        GarminCloudStore store = connected();
        GarminHealthClient client = new GarminHealthClient(fixture);
        JSONObject result = client.read(store, store.sessionId(), DAY, "heart_rate");
        assertEquals(2, fixture.urls.size());
        assertEquals(GarminHealthClient.PROFILE_URL, fixture.urls.get(0));
        assertTrue(fixture.urls.get(1).contains("/test%2Fname%3Fx%23y?date="));
        assertFalse(result.toString().contains("PRIVATE"));
        assertFalse(result.toString().contains("test/name"));
        client.read(store, store.sessionId(), DAY, "steps");
        assertEquals(3, fixture.urls.size());
        store.login(TOKEN, null);
        assertNull(store.displayName());
        client.read(store, store.sessionId(), DAY, "resting_heart_rate");
        assertEquals(5, fixture.urls.size());
        assertEquals(GarminHealthClient.PROFILE_URL, fixture.urls.get(3));
    }

    @Test public void missingDisplayNameCannotBecomeAPathOrLeakProfile() throws Exception {
        Fixture fixture = new Fixture();
        fixture.profile = "{\"displayName\":\"\",\"email\":\"PRIVATE\"}";
        GarminCloudStore store = connected();
        assertEquals("profile_unavailable", assertThrows(GarminCloudClient.Failure.class,
            () -> new GarminHealthClient(fixture).read(store, store.sessionId(), DAY, "heart_rate")).code);
        assertEquals(1, fixture.urls.size());
        assertNull(store.displayName());
        assertEquals("%2E%2E%2F%3Fx%23%26%3D%25", GarminHealthClient.encodePath("../?x#&=%"));
        assertFalse(GarminHealthClient.validDisplayName("bad\nname"));
        assertFalse(GarminHealthClient.validDisplayName("a".repeat(257)));
    }

    @Test public void mapsMissingAndEmptyPayloadsToUnavailableWithoutInventingZeroes() throws Exception {
        for (int status : new int[]{204, 403, 404}) assertSame(JSONObject.NULL,
            GarminHealthClient.payload(new GarminHealthClient.Response(status, "PRIVATE-not-json")));
        for (String body : new String[]{null, "", " \n", "null", "{}", "[]", "{\"data\":[]}", "{\"values\":[null,{}]}"}) {
            Fixture fixture = new Fixture(); fixture.body = body;
            GarminCloudStore store = connected();
            JSONObject result = new GarminHealthClient(fixture).read(store, store.sessionId(), DAY, "weight");
            assertEquals("unavailable", result.getString("status"));
            assertFalse(result.has("data"));
            assertFalse(result.has("error"));
        }
    }

    @Test public void distinguishesAuthenticationRateLimitNetworkAndInvalidPayloadWithoutBodies() {
        failure("auth_required", 401, "PRIVATE");
        failure("rate_limited", 429, "PRIVATE");
        failure("health_failed", 302, "PRIVATE");
        failure("health_failed", 500, "PRIVATE");
        failure("invalid_response", 200, "<html>PRIVATE</html>");
        failure("invalid_response", 200, "{} []");
        failure("invalid_response", 200, "42");
    }

    @Test public void privateMetricDoesNotRevokeTheSharedUploadSession() throws Exception {
        Fixture fixture = new Fixture();
        fixture.body = "{\"privacyProtected\":true,\"reading\":42}";
        GarminCloudStore store = connected();
        String session = store.sessionId();
        JSONObject result = new GarminHealthClient(fixture).read(store, session, DAY, "weight");
        assertEquals("unavailable", result.getString("status"));
        assertFalse(result.has("data"));
        assertFalse(result.has("error"));
        assertTrue(store.connected());
        assertEquals(session, store.sessionId());
        assertEquals(TOKEN, store.token());
        assertSame(JSONObject.NULL, GarminHealthClient.payload(new GarminHealthClient.Response(200, fixture.body)));
    }

    @Test public void preservesNumericUnitsZeroNullAndAllSafeTimeSeriesAndTemperatureFields() throws Exception {
        Fixture fixture = new Fixture();
        fixture.body = "{\"weight\":70125.5,\"bodyFat\":16.2,\"sleepTimeSeconds\":21600,\"sleepStartTimestampGMT\":1760000000123,"
            + "\"avgSleepHRV\":47.5,\"averageSpo2\":98,\"skinTempData\":{\"deviation\":-0.25,\"unit\":\"celsius\"},"
            + "\"values\":[[1760000000123,0],[1760000060123,null]],\"missing\":null,\"sourceId\":123,\"sessions\":[{\"duration\":120}]}";
        GarminCloudStore store = connected();
        JSONObject data = new GarminHealthClient(fixture).read(store, store.sessionId(), DAY, "sleep").getJSONObject("data");
        assertEquals(70125.5, data.getDouble("weight"), 0);
        assertEquals(21600, data.getInt("sleepTimeSeconds"));
        assertEquals(1760000000123L, data.getLong("sleepStartTimestampGMT"));
        assertEquals(-0.25, data.getJSONObject("skinTempData").getDouble("deviation"), 0);
        assertEquals(0, data.getJSONArray("values").getJSONArray(0).getInt(1));
        assertTrue(data.getJSONArray("values").getJSONArray(1).isNull(1));
        assertTrue(data.isNull("missing"));
        assertEquals(120, data.getJSONArray("sessions").getJSONObject(0).getInt("duration"));
    }

    @Test public void stripsCredentialKeysRecursivelyButKeepsSourceIdsAndNeverReturnsWholeProfile() throws Exception {
        Fixture fixture = new Fixture();
        fixture.body = "{\"access_token\":\"PRIVATE\",\"Authorization\":\"PRIVATE\",\"nested\":[{\"password\":\"PRIVATE\","
            + "\"refreshToken\":\"PRIVATE\",\"connect-csrf-token\":\"PRIVATE\",\"headers\":{\"x\":\"PRIVATE\"},"
            + "\"userProfile\":{\"address\":\"PRIVATE\"},\"userProfilePK\":123,\"reading\":7}],\"Cookie\":\"PRIVATE\",\"sessionId\":\"PRIVATE\"}";
        GarminCloudStore store = connected();
        JSONObject result = new GarminHealthClient(fixture).read(store, store.sessionId(), DAY, "weight");
        assertFalse(result.toString().contains("PRIVATE"));
        assertEquals(123, result.getJSONObject("data").getJSONArray("nested").getJSONObject(0).getInt("userProfilePK"));
    }

    @Test public void rejectsOversizedUtf8AndDeepOrComplexJsonBeforeParsingWithoutTruncation() {
        failure("response_too_large", 200, "{\"x\":\"" + "a".repeat(GarminHealthClient.MAX_RESPONSE_BYTES) + "\"}");
        failure("response_too_large", 200, "{\"x\":\"" + "é".repeat(GarminHealthClient.MAX_RESPONSE_BYTES / 2) + "\"}");
        failure("response_too_complex", 200, "[".repeat(33) + "0" + "]".repeat(33));
        failure("response_too_complex", 200, "[" + "0,".repeat(GarminHealthClient.MAX_NODES) + "0]");
        failure("invalid_response", 200, "{'x':[]}");
        failure("invalid_response", 200, "{/*comment*/\"x\":1}");
        failure("invalid_response", 200, "[)");
    }

    @Test public void rejectsHostSchemesPortsRedirectTargetsAndRawEcgFiles() {
        for (String url : new String[]{"http://connectapi.garmin.com/", "https://evil.test/", "https://connectapi.garmin.com.evil.test/",
            "https://user@connectapi.garmin.com/", "https://connectapi.garmin.com:443/", "https://connectapi.garmin.com/#private",
            "https://ghs.garmin.com/ghs/ecg/v1/ecg/raw-file", "file:///private", "https://sso.garmin.com/"})
            assertFalse(url, GarminHealthClient.allowedUrl(url));
    }

    @Test public void sharedGetHeadersContainNativeAuthOnlyAndNoMultipartOrCallerHeaders() throws Exception {
        Map<String, String> headers = GarminCloudClient.authHeaders(TOKEN, "csrf");
        assertEquals("JWT_WEB=" + TOKEN, headers.get("Cookie"));
        assertFalse(headers.containsKey("Content-Type"));
        assertFalse(headers.containsKey("Authorization"));
        assertEquals("csrf", headers.get("connect-csrf-token"));
        assertThrows(GarminCloudClient.Failure.class, () -> GarminCloudClient.authHeaders("bad\r\nInjected:yes", null));
    }

    @Test public void boundedErrorEnvelopeEchoesNoBodyAndNoUnboundedInput() throws Exception {
        JSONObject error = GarminHealthClient.error("a".repeat(5000), "PRIVATE", "auth_required");
        assertEquals("error", error.getString("status"));
        assertEquals("auth_required", error.getString("error"));
        assertEquals("", error.getString("metric"));
        assertEquals("", error.getString("date"));
        assertFalse(error.has("data"));
    }
}
