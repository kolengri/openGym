package ch.duartesantos.opengym;

import com.getcapacitor.JSObject;
import com.getcapacitor.PluginCall;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import org.junit.Test;
import static org.junit.Assert.*;

public class GarminCloudStatusTest {
    @Test public void nativeStatusFailureRejectsInsteadOfReportingMissingCredentials() throws Exception {
        RecordingCall call = new RecordingCall();
        // An unattached native bridge cannot provide the storage context. Exercise the actual
        // asynchronous status failure handler without accessing a device or real credentials.
        new GarminCloudPlugin().status(call);
        assertTrue(call.completed.await(5, TimeUnit.SECONDS));
        assertNull(call.result);
        assertEquals("storage_unavailable", call.error);
    }

    private static final class RecordingCall extends PluginCall {
        final CountDownLatch completed = new CountDownLatch(1);
        JSObject result;
        String error;
        RecordingCall() { super(null, "GarminCloud", "synthetic", "status", new JSObject()); }
        @Override public void resolve(JSObject result) { this.result = result; completed.countDown(); }
        @Override public void reject(String message, String code) { error = code; completed.countDown(); }
    }
}
