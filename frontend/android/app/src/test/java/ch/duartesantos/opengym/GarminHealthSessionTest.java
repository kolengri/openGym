package ch.duartesantos.opengym;

import org.json.JSONObject;
import org.junit.Test;
import java.util.ArrayList;
import java.util.List;
import static org.junit.Assert.*;

/** Exercise the bridge's durable session transition, not only the HTTP error parser. */
public class GarminHealthSessionTest {
    private static final String TOKEN = "synthetic.payload.signature";
    private static final String DAY = "2026-01-02";
    static final class Transport implements GarminHealthClient.Transport {
        final List<String> urls = new ArrayList<>();
        int profileStatus = 200;
        String profileBody = "{\"displayName\":\"synthetic\"}";
        boolean offline;
        @Override public GarminHealthClient.Response get(String url, String token, String csrf) throws GarminCloudClient.Failure {
            assertEquals(TOKEN, token);
            urls.add(url);
            if (url.equals(GarminHealthClient.PROFILE_URL)) {
                if (offline) throw new GarminCloudClient.Failure("network_error");
                return new GarminHealthClient.Response(profileStatus, profileBody);
            }
            return new GarminHealthClient.Response(url.contains("/ecg/") ? 401 : 200, "{\"reading\":42}");
        }
    }
    private GarminCloudStore connected(GarminCloudStoreTest.Disk disk) throws Exception {
        GarminCloudStore store = new GarminCloudStore(disk);
        store.login(TOKEN, "synthetic-csrf");
        return store;
    }
    private JSONObject read(GarminCloudStore store, String session, Transport transport, String metric) throws Exception {
        return GarminCloudPlugin.readHealthOnce(store, session, DAY, metric, new GarminHealthClient(transport));
    }

    @Test public void metricUnauthorizedDoesNotLogOutAnOtherwiseValidAccountOnRepeatedReadsOrRestart() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        GarminCloudStore store = connected(disk);
        String session = store.sessionId();
        Transport transport = new Transport();
        assertEquals("available", read(store, session, transport, "weight").getString("status"));
        JSONObject error = read(store, session, transport, "ecg");
        assertEquals("health_failed", error.getString("error"));
        assertFalse(error.toString().contains(TOKEN));
        for (int i = 0; i < 2; i++) {
            store = new GarminCloudStore(disk);
            assertEquals(session, store.sessionId());
            assertEquals(TOKEN, store.token());
            assertEquals("available", read(store, session, transport, "weight").getString("status"));
        }
        assertEquals(5, transport.urls.size()); // Three reads, rejected ECG, one auth probe.
        assertEquals(GarminHealthClient.PROFILE_URL, transport.urls.get(2));
    }

    @Test public void confirmedAccountUnauthorizedStillInvalidatesCredentialsAndKeepsUnknownUploadReceipt() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        GarminCloudStore store = connected(disk);
        String session = store.sessionId();
        store.begin(session, "queued", "a".repeat(64), false);
        Transport transport = new Transport(); transport.profileStatus = 401;
        assertEquals("auth_required", read(store, session, transport, "ecg").getString("error"));
        GarminCloudStore restarted = new GarminCloudStore(disk);
        assertFalse(restarted.connected());
        assertTrue(restarted.uncertain("queued"));
        assertEquals(2, transport.urls.size());
    }

    @Test public void inconclusiveAuthProbeNeverErasesCredentials() throws Exception {
        for (int status : new int[]{204, 403, 404, 429, 500}) {
            GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
            GarminCloudStore store = connected(disk);
            String session = store.sessionId(), before = disk.value;
            Transport transport = new Transport(); transport.profileStatus = status;
            assertEquals(status == 429 ? "rate_limited" : "health_failed", read(store, session, transport, "ecg").getString("error"));
            assertEquals(before, disk.value);
            assertEquals(session, new GarminCloudStore(disk).sessionId());
            assertEquals(2, transport.urls.size());
        }
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        GarminCloudStore store = connected(disk);
        Transport transport = new Transport(); transport.offline = true;
        assertEquals("network_error", read(store, store.sessionId(), transport, "ecg").getString("error"));
        assertTrue(new GarminCloudStore(disk).connected());
    }

    @Test public void staleProfileRequestCannotProbeOrInvalidateTheCurrentSession() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        GarminCloudStore store = connected(disk);
        String stale = store.sessionId();
        store.login(TOKEN, null);
        Transport transport = new Transport();
        assertEquals("auth_required", read(store, stale, transport, "ecg").getString("error"));
        assertTrue(new GarminCloudStore(disk).connected());
        assertTrue(transport.urls.isEmpty());
    }

    @Test public void malformedOrEmptyProbeCannotBecomeAnAccountLogout() throws Exception {
        for (String body : new String[]{"", "<html>Sign in</html>", "{broken"}) {
            GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
            GarminCloudStore store = connected(disk);
            String before = disk.value;
            Transport transport = new Transport(); transport.profileBody = body;
            assertEquals(body.isEmpty() ? "health_failed" : "invalid_response",
                read(store, store.sessionId(), transport, "ecg").getString("error"));
            assertEquals(before, disk.value);
            assertEquals(2, transport.urls.size());
        }
    }

    @Test public void unauthorizedPrimaryProfileIsNotProbedAgain() throws Exception {
        GarminCloudStoreTest.Disk disk = new GarminCloudStoreTest.Disk();
        GarminCloudStore store = connected(disk);
        Transport transport = new Transport(); transport.profileStatus = 401;
        assertEquals("auth_required", read(store, store.sessionId(), transport, "heart_rate").getString("error"));
        assertFalse(new GarminCloudStore(disk).connected());
        assertEquals(List.of(GarminHealthClient.PROFILE_URL), transport.urls);
    }
}
