package ch.duartesantos.opengym;

import android.content.Context;
import java.util.concurrent.atomic.AtomicLong;

/** Native DI refresh. No WebView, browser cookies, or account-profile dependency. */
final class GarminCloudRenewal {
    private static final AtomicLong EPOCH = new AtomicLong();
    static long lease() { return EPOCH.get(); }
    /** Revoke synchronously before the IO queue processes disconnect or a new login. */
    static void cancelPending() { EPOCH.incrementAndGet(); }

    static GarminCloudSession.Renewal forOperation(Context context, long epoch) {
        return new GarminCloudSession.Renewal() {
            @Override public GarminCloudSession.Credentials fetch(GarminCloudSession.Credentials previous) throws GarminCloudClient.Failure {
                check();
                GarminCloudSession.Credentials fresh = new GarminCloudAuth().refresh(previous);
                check();
                return fresh;
            }
            @Override public void check() throws GarminCloudClient.Failure { checkLease(epoch); }
        };
    }
    static void checkLease(long epoch) throws GarminCloudClient.Failure {
        if (epoch != EPOCH.get()) throw new GarminCloudClient.Failure("cancelled");
    }
}
