package ch.duartesantos.opengym;

import android.content.Context;
import android.content.pm.PackageManager;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.util.AtomicFile;
import com.garmin.android.connectiq.ConnectIQ;
import com.garmin.android.connectiq.IQApp;
import com.garmin.android.connectiq.IQDevice;
import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
import java.util.Collections;
import java.util.List;
import java.util.LinkedHashSet;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.RejectedExecutionException;

/**
 * Garmin Connect owns the radio. No wake lock, continuous WebView execution or phone-side
 * workout recording: the watch works locally and retries its durable commands on reconnection.
 */
@CapacitorPlugin(name = "GarminBridge")
public class GarminBridgePlugin extends Plugin {
    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private final Handler main = new Handler(Looper.getMainLooper());
    private final IQApp app = new IQApp(GarminProtocol.APP_ID);
    private final ArrayDeque<JSONObject> outbound = new ArrayDeque<>();
    private final Set<String> pendingAckIds = new LinkedHashSet<>();
    private GarminLinkStore.Storage storage;
    private GarminLinkStore store;
    private volatile ConnectIQ sdk;
    private IQDevice selected;
    private boolean ready, initializing, installed, connected, sending, replayAcks;
    private volatile boolean destroyed;
    private long generation, lastHrAt = -5000, sendStarted, sendToken, initStarted;
    private volatile long sdkGeneration;
    private String error, lastStatus;

    @Override
    public void load() {
        Context context = getContext().getApplicationContext();
        AtomicFile file = new AtomicFile(new File(context.getNoBackupFilesDir(), "garmin-link.json"));
        storage = new GarminLinkStore.Storage() {
            @Override public String read() throws Exception {
                if (!file.getBaseFile().exists() && !new File(file.getBaseFile().getPath() + ".bak").exists()) return null;
                try (FileInputStream in = file.openRead(); ByteArrayOutputStream bytes = new ByteArrayOutputStream()) {
                    byte[] buffer = new byte[4096];
                    int count;
                    while ((count = in.read(buffer)) != -1) {
                        if (bytes.size() + count > GarminLinkStore.MAX_STORE_BYTES)
                            throw new IllegalStateException("Garmin queue storage is too large; disable the link to reset it");
                        bytes.write(buffer, 0, count);
                    }
                    return bytes.toString(StandardCharsets.UTF_8.name());
                }
            }

            @Override public void write(String value) throws Exception {
                FileOutputStream out = null;
                try {
                    out = file.startWrite();
                    out.write(value.getBytes(StandardCharsets.UTF_8));
                    file.finishWrite(out);
                } catch (Exception e) {
                    if (out != null) file.failWrite(out);
                    throw e;
                }
            }
        };
        dispatch(() -> {
            try {
                store = new GarminLinkStore(storage);
                if (store.enabled()) startSdk();
            } catch (Exception e) { error = "Garmin queue could not be read; disable the link to reset it"; }
            changed();
            scheduleRetry();
        });
    }

    @PluginMethod public void status(PluginCall call) {
        dispatch(() -> call.resolve(state()));
    }

    @PluginMethod public void devices(PluginCall call) {
        dispatch(() -> {
            startSdk();
            JSONArray devices = new JSONArray();
            try {
                for (IQDevice device : knownDevices()) {
                    devices.put(new JSONObject().put("id", deviceId(device))
                        .put("name", device.getFriendlyName() == null ? "Garmin" : device.getFriendlyName())
                        .put("connected", sdk.getDeviceStatus(device) == IQDevice.IQDeviceStatus.CONNECTED));
                }
                call.resolve(new JSObject().put("devices", devices));
            } catch (Exception e) { call.reject("Could not list Garmin devices; open Garmin Connect and try again"); }
        });
    }

    @PluginMethod public void configure(PluginCall call) {
        dispatch(() -> {
            try {
                Object value = call.getData().opt("enabled");
                if (!(value instanceof Boolean)) throw new IllegalArgumentException("Garmin enabled must be a boolean");
                boolean enabled = (Boolean) value;
                if (!enabled && store == null) {
                    GarminLinkStore.reset(storage);
                    store = new GarminLinkStore(storage);
                }
                requireStore();
                String id = call.getString("deviceId", store.deviceId());
                if (enabled) {
                    startSdk();
                    if (!ready) throw new IllegalStateException("Garmin Connect is starting; try again");
                    boolean found = false;
                    for (IQDevice device : knownDevices()) if (deviceId(device).equals(id)) found = true;
                    if (!found) throw new IllegalArgumentException("Select a paired Garmin device first");
                }
                if (store.configure(enabled, id)) {
                    unregister();
                    lastHrAt = -5000;
                    error = null;
                }
                if (enabled) refresh();
                else stopSdk();
                scheduleRetry();
                changed();
                call.resolve(state());
            } catch (Exception e) { reject(call, e); }
        });
    }

    @PluginMethod public void sendSnapshot(PluginCall call) {
        dispatch(() -> {
            try {
                requireStore();
                if (!store.enabled()) { call.resolve(new JSObject().put("sent", false)); return; }
                store.setSnapshot(call.getString("json"));
                flush();
                call.resolve(new JSObject().put("sent", ready && connected && installed && !store.pending()));
            } catch (Exception e) { reject(call, e); }
        });
    }

    @PluginMethod public void drain(PluginCall call) {
        dispatch(() -> {
            try {
                requireStore();
                call.resolve(new JSObject().put("events", store.enabled() ? store.events() : new JSONArray()));
            } catch (Exception e) { reject(call, e); }
        });
    }

    @PluginMethod public void ack(PluginCall call) {
        dispatch(() -> {
            try {
                requireStore();
                JSArray ids = call.getArray("ids");
                // The resulting snapshot is supplied only after the web workout store's saveNow.
                store.acknowledge(ids, call.getString("json"));
                for (int i = 0; i < ids.length(); i++) requestAck(ids.getString(i));
                flush();
                call.resolve();
            } catch (Exception e) { reject(call, e); }
        });
    }

    @PluginMethod public void openOnWatch(PluginCall call) {
        dispatch(() -> {
            if (store == null || !store.enabled() || !ready || selected == null || !connected || !installed) {
                call.reject("Connect the selected Garmin watch and install its openGym companion first");
                return;
            }
            try {
                long epoch = generation;
                IQDevice target = selected;
                // Acknowledges the request, not physical launch; Garmin may show a confirmation on the watch.
                sdk.openApplication(selected, app, (device, application, result) -> dispatch(() -> {
                    if (!current(epoch, target)) return;
                    if (result == ConnectIQ.IQOpenApplicationStatus.APP_IS_NOT_INSTALLED) {
                        installed = false;
                        error = "Install the openGym companion on the selected Garmin watch";
                        changed();
                    }
                }));
                call.resolve(new JSObject().put("requested", true));
            } catch (Exception e) { call.reject("Could not open the Garmin companion; reconnect the watch and retry"); }
        });
    }

    @PluginMethod public void openStore(PluginCall call) {
        dispatch(() -> {
            startSdk();
            if (!ready) { call.reject("Garmin Connect is starting; try again"); return; }
            try {
                // Store IDs differ from the manifest UUID used for local communication.
                sdk.openStore("10ea70db-ee8f-4811-9b65-ec251468afae");
                call.resolve(new JSObject().put("requested", true));
            } catch (Exception ignored) { call.reject("Could not open the Garmin installation page"); }
        });
    }

    private void startSdk() {
        if (ready || destroyed) return;
        if (initializing) {
            if (SystemClock.elapsedRealtime() - initStarted < 30_000) return;
            stopSdk();
        }
        if (!available()) { error = "Install or update Garmin Connect on this phone"; changed(); return; }
        initializing = true;
        initStarted = SystemClock.elapsedRealtime();
        Context context = getContext().getApplicationContext();
        final long sdkEpoch = ++sdkGeneration;
        main.post(() -> initializeSdk(context, sdkEpoch));
    }

    private void initializeSdk(Context context, long sdkEpoch) {
        if (destroyed || sdkGeneration != sdkEpoch) return;
        try {
            ConnectIQ instance = ConnectIQ.getInstance(context, ConnectIQ.IQConnectType.WIRELESS);
            sdk = instance;
            instance.initialize(context, false, new ConnectIQ.ConnectIQListener() {
                @Override public void onSdkReady() { dispatch(() -> {
                    if (sdkGeneration != sdkEpoch) return;
                    ready = true;
                    initializing = false;
                    error = null;
                    refresh();
                    changed();
                }); }
                @Override public void onInitializeError(ConnectIQ.IQSdkErrorStatus status) { dispatch(() -> {
                    if (sdkGeneration != sdkEpoch) return;
                    ready = false;
                    initializing = false;
                    error = "Garmin Connect is unavailable; open or update it and retry";
                    changed();
                }); }
                @Override public void onSdkShutDown() { dispatch(() -> {
                    if (sdkGeneration != sdkEpoch) return;
                    ready = false;
                    initializing = false;
                    selected = null;
                    connected = installed = sending = false;
                    outbound.clear();
                    pendingAckIds.clear();
                    generation++;
                    changed();
                }); }
            });
            if (sdkGeneration != sdkEpoch || destroyed) {
                try { instance.shutdown(context); } catch (Exception ignored) { }
            }
        } catch (Exception e) { dispatch(() -> {
                if (sdkGeneration != sdkEpoch) return;
                initializing = false;
                error = "Garmin Connect could not start; open or update it and retry";
                changed();
            }); }
    }

    private List<IQDevice> knownDevices() throws Exception {
        if (!ready) return Collections.emptyList();
        List<IQDevice> result = sdk.getKnownDevices();
        return result == null ? Collections.emptyList() : result;
    }

    private void refresh() {
        if (!ready || store == null || !store.enabled()) return;
        try {
            IQDevice found = null;
            for (IQDevice d : knownDevices()) if (deviceId(d).equals(store.deviceId())) found = d;
            if (found == null) {
                if (selected != null) unregister();
                error = "The selected watch is no longer paired in Garmin Connect";
                changed();
                return;
            }
            if (selected == null) {
                selected = found;
                final long epoch = generation;
                sdk.registerForDeviceEvents(selected, (device, status) -> dispatch(() -> {
                    if (!current(epoch, device)) return;
                    boolean wasConnected = connected;
                    connected = status == IQDevice.IQDeviceStatus.CONNECTED;
                    if (connected && !wasConnected) replayAcks = true;
                    if (!connected) { outbound.clear(); sending = false; sendToken++; }
                    refresh();
                    changed();
                }));
                sdk.registerForAppEvents(selected, app, (device, application, messages, status) -> dispatch(() -> {
                    if (!current(epoch, device) || status != ConnectIQ.IQMessageStatus.SUCCESS
                        || application == null || application.getApplicationId() == null || !GarminProtocol.APP_ID.equals(
                            application.getApplicationId().replace("-", "").toLowerCase(Locale.ROOT))) return;
                    receive(messages);
                }));
                replayAcks = true;
            }
            connected = sdk.getDeviceStatus(selected) == IQDevice.IQDeviceStatus.CONNECTED;
            final long epoch = generation;
            sdk.getApplicationInfo(GarminProtocol.APP_ID, selected, new ConnectIQ.IQApplicationInfoListener() {
                @Override public void onApplicationInfoReceived(IQApp info) { dispatch(() -> {
                    if (!current(epoch, selected)) return;
                    installed = info != null && info.getStatus() == IQApp.IQAppStatus.INSTALLED;
                    if (installed) error = null;
                    flush();
                    changed();
                }); }
                @Override public void onApplicationNotInstalled(String applicationId) { dispatch(() -> {
                    if (!current(epoch, selected)) return;
                    installed = false;
                    error = "Install the openGym companion on the selected Garmin watch";
                    changed();
                }); }
            });
            flush();
            changed();
        } catch (Exception e) {
            stopSdk();
            error = "Garmin Connect is unavailable; open it and reconnect the selected watch";
            changed();
        }
    }

    private boolean current(long epoch, IQDevice device) {
        return !destroyed && generation == epoch && store != null && store.enabled()
            && selected != null && device != null && deviceId(device).equals(store.deviceId());
    }

    private void receive(List<Object> messages) {
        if (messages == null || messages.size() > GarminProtocol.MAX_BATCH) {
            error = "Invalid Garmin message batch"; changed(); return;
        }
        for (Object value : messages) {
            try {
                JSONObject message = GarminProtocol.incoming(value);
                switch (message.getString("kind")) {
                    case "hello":
                        replayAcks = true;
                        if (store.pending()) notifyListeners("watchEvent", new JSObject());
                        flush();
                        break;
                    case "events":
                        if (store.receive(message.getJSONArray("events")))
                            notifyListeners("watchEvent", new JSObject());
                        // A duplicate may be a lost ack. Only persisted ack history is replayed.
                        JSONArray events = message.getJSONArray("events");
                        for (int i = 0; i < events.length(); i++)
                            requestAck(events.getJSONObject(i).getString("id"));
                        flush();
                        break;
                    case "hr":
                        long now = SystemClock.elapsedRealtime();
                        if (now - lastHrAt >= 5000) {
                            lastHrAt = now;
                            notifyListeners("heartRate", new JSObject(message.toString()));
                        }
                        break;
                    default: break;
                }
            } catch (Exception e) { error = safeError(e); changed(); }
        }
    }

    private void requestAck(String id) {
        if (replayAcks) return;
        pendingAckIds.add(id);
        if (pendingAckIds.size() > GarminLinkStore.MAX_ACKED) {
            pendingAckIds.clear();
            replayAcks = true;
        }
    }

    /** One SDK send at a time: SDK listeners are scoped to app/device, not a message ID. */
    private void flush() {
        if (destroyed || store == null || !store.enabled() || !ready || !connected || !installed || selected == null) return;
        if (sending && SystemClock.elapsedRealtime() - sendStarted < 30_000) return;
        if (sending) { sending = false; outbound.clear(); sendToken++; replayAcks = true; }
        try {
            if (outbound.isEmpty()) {
                JSONArray acks = replayAcks ? store.ackPackets()
                    : store.ackPacketsFor(new JSONArray(pendingAckIds));
                for (int i = 0; i < acks.length(); i++) outbound.add(acks.getJSONObject(i));
                replayAcks = false;
                pendingAckIds.clear();
                JSONObject snapshot = store.snapshot();
                if (snapshot != null && (outbound.isEmpty()
                    || snapshot.getLong("seq") > outbound.getLast().getLong("seq"))) outbound.add(snapshot);
            }
            sendNext();
        } catch (Exception e) { replayAcks = true; error = safeError(e); changed(); }
    }

    private void sendNext() throws Exception {
        if (outbound.isEmpty() || sending || !connected) return;
        JSONObject packet = outbound.removeFirst();
        long epoch = generation;
        IQDevice target = selected;
        long token = ++sendToken;
        sending = true;
        sendStarted = SystemClock.elapsedRealtime();
        try {
            sdk.sendMessage(target, app, GarminProtocol.wire(packet), (device, application, result) -> dispatch(() -> {
                if (!current(epoch, target) || token != sendToken) return;
                sending = false;
                if (result != ConnectIQ.IQMessageStatus.SUCCESS) {
                    outbound.clear();
                    replayAcks = true;
                    error = "Garmin send failed; the saved link will retry on reconnection";
                    changed();
                    return;
                }
                error = null;
                try {
                    if (!outbound.isEmpty()) sendNext();
                    // A newer snapshot/ack may have been persisted while this send was in flight.
                    else if (replayAcks || !pendingAckIds.isEmpty() || (store.snapshot() != null
                        && store.snapshot().getLong("seq") > packet.optLong("seq"))) flush();
                } catch (Exception e) { error = safeError(e); }
                changed();
            }));
        } catch (Exception e) {
            sending = false;
            outbound.clear();
            replayAcks = true;
            throw e;
        }
    }

    private void unregister() {
        generation++;
        sendToken++;
        if (sdk != null && ready) {
            try { sdk.unregisterAllForEvents(); } catch (Exception ignored) { }
        }
        selected = null;
        connected = installed = sending = false;
        outbound.clear();
        pendingAckIds.clear();
        replayAcks = true;
    }

    private void stopSdk() {
        sdkGeneration++;
        unregister();
        if (sdk != null) {
            try { sdk.shutdown(getContext().getApplicationContext()); } catch (Exception ignored) { }
        }
        sdk = null;
        ready = initializing = false;
    }

    private boolean available() {
        try {
            getContext().getPackageManager().getPackageInfo("com.garmin.android.apps.connectmobile", 0);
            return true;
        } catch (PackageManager.NameNotFoundException e) { return false; }
    }

    private JSObject state() {
        JSObject result = new JSObject().put("available", available()).put("activated", ready)
            .put("enabled", store != null && store.enabled()).put("paired", selected != null)
            .put("installed", installed).put("connected", connected);
        if (store != null && store.enabled()) result.put("deviceId", store.deviceId());
        if (selected != null) result.put("deviceName", selected.getFriendlyName());
        if (error != null) result.put("error", error);
        return result;
    }

    private void changed() {
        JSObject status = state();
        if (!status.toString().equals(lastStatus)) {
            lastStatus = status.toString();
            notifyListeners("watchState", status);
        }
    }

    private void requireStore() {
        if (store == null) throw new IllegalStateException("Garmin queue is unavailable; disable the link to reset it");
    }

    private static String deviceId(IQDevice device) { return Long.toString(device.getDeviceIdentifier()); }

    private static String safeError(Exception error) {
        if (error instanceof IllegalArgumentException || error instanceof IllegalStateException) return error.getMessage();
        return "Garmin data could not be persisted or processed; nothing was acknowledged";
    }

    private void reject(PluginCall call, Exception failure) {
        error = safeError(failure);
        changed();
        call.reject(error);
    }

    private void dispatch(Runnable task) {
        if (destroyed) return;
        try { io.execute(task); } catch (RejectedExecutionException ignored) { }
    }

    private final Runnable retry = () -> dispatch(() -> {
        if (store != null && store.enabled()) {
            startSdk();
            refresh();
        }
        scheduleRetry();
    });

    private void scheduleRetry() {
        main.removeCallbacks(retry);
        if (!destroyed && store != null && store.enabled()) main.postDelayed(retry, 15_000);
    }

    @Override protected void handleOnResume() { dispatch(() -> {
        if (store != null && store.enabled()) { startSdk(); refresh(); }
        if (store != null && store.pending()) notifyListeners("watchEvent", new JSObject());
    }); }

    @Override protected void handleOnDestroy() {
        main.removeCallbacks(retry);
        dispatch(this::stopSdk);
        destroyed = true;
        io.shutdown();
    }
}
