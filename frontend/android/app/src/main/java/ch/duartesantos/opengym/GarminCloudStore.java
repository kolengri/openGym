package ch.duartesantos.opengym;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.AtomicFile;
import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** Credentials and receipts stay native, encrypted together, and outside Android backups. */
final class GarminCloudStore {
    static final ExecutorService IO = Executors.newSingleThreadExecutor();
    static final int MAX_RECEIPTS = 512;
    static final int MAX_STORE_BYTES = 512 * 1024;
    interface Storage {
        String read() throws Exception;
        void write(String value) throws Exception;
        void clear() throws Exception;
    }

    private final Storage storage;
    private JSONObject state;

    GarminCloudStore(Storage storage) throws Exception {
        this.storage = storage;
        String value = storage.read();
        state = value == null ? empty() : new JSONObject(value);
        if (state.getInt("v") != 1 || state.getJSONArray("receipts").length() > MAX_RECEIPTS)
            throw new IllegalStateException("Invalid Garmin storage");
        String token = state.optString("token", "");
        if (!token.isEmpty() && (!GarminCloudClient.validToken(token)
            || !GarminCloudClient.validCsrf(csrf()) || !validSession(sessionId())))
            throw new IllegalStateException("Invalid Garmin storage");
        JSONArray receipts = state.getJSONArray("receipts");
        // Migrate the old session-scoped journal without forgetting its original owner.
        String legacyGeneration = validSession(sessionId()) ? sessionId() : UUID.randomUUID().toString();
        for (int i = 0; i < receipts.length(); i++) {
            JSONObject entry = receipts.getJSONObject(i);
            if (!entry.has("generation")) entry.put("generation", legacyGeneration);
            if (!validSession(entry.getString("generation"))
                || !entry.getString("workout").matches("[a-f0-9]{64}")
                || !entry.getString("sha").matches("[a-f0-9]{64}")
                || !(entry.getString("status").equals("inflight") || entry.getString("status").equals("uploaded")
                    || entry.getString("status").equals("duplicate")))
                throw new IllegalStateException("Invalid Garmin receipts");
        }
    }

    private static JSONObject empty() throws Exception {
        return new JSONObject().put("v", 1).put("receipts", new JSONArray());
    }

    static boolean validSession(String value) {
        return value != null && value.matches("[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}");
    }

    boolean connected() { return GarminCloudClient.validToken(token()); }
    String sessionId() { return state.optString("session", null); }
    String token() { return state.optString("token", null); }
    String csrf() { return state.optString("csrf", null); }

    void requireSession(String session) throws GarminCloudClient.Failure {
        if (!connected() || !validSession(session) || !session.equals(sessionId()))
            throw new GarminCloudClient.Failure("auth_required");
    }

    /** Durable nonce: all callers must use IO, including Activity lifecycle/result callbacks. */
    String startLogin() throws Exception {
        JSONObject next = withoutCredentials(copy());
        String nonce = UUID.randomUUID().toString();
        next.put("loginNonce", nonce);
        persist(next);
        return nonce;
    }

    String cancellationNonce() {
        return state.optString("loginNonce", state.optString("loginResultNonce", null));
    }

    static boolean sameLoginNonce(String first, String second) {
        return validSession(first) && first.equals(second);
    }

    boolean pendingLogin(String nonce) { return sameLoginNonce(nonce, state.optString("loginNonce", null)); }

    boolean loginResultMatches(String nonce) {
        return connected() && sameLoginNonce(nonce, state.optString("loginResultNonce", null));
    }

    void finishLogin(String nonce, String token, String csrf) throws Exception {
        if (!pendingLogin(nonce)) throw new GarminCloudClient.Failure("cancelled");
        saveCredentials(token, csrf, nonce);
    }

    // Package seam for offline store tests; production login always uses finishLogin's nonce fence.
    void login(String token, String csrf) throws Exception { saveCredentials(token, csrf, null); }

    private void saveCredentials(String token, String csrf, String nonce) throws Exception {
        if (!GarminCloudClient.validToken(token) || !GarminCloudClient.validCsrf(csrf))
            throw new GarminCloudClient.Failure("auth_required");
        JSONObject next = withoutCredentials(copy());
        next.put("token", token).put("session", UUID.randomUUID().toString());
        if (csrf != null) next.put("csrf", csrf);
        if (nonce != null) next.put("loginResultNonce", nonce);
        persist(next);
    }

    private JSONObject withoutCredentials(JSONObject next) {
        for (String key : new String[]{"token", "csrf", "session", "displayName", "loginNonce", "loginResultNonce"})
            next.remove(key);
        return next;
    }

    void invalidate() throws Exception { persist(withoutCredentials(copy())); }
    void disconnect() throws Exception { invalidate(); }

    void cancelLogin(String nonce) throws Exception {
        if (pendingLogin(nonce) || loginResultMatches(nonce)) invalidate();
    }

    String displayName() { return state.optString("displayName", null); }
    void cacheDisplayName(String session, String name) throws Exception {
        requireSession(session);
        if (!GarminHealthClient.validDisplayName(name)) throw new GarminCloudClient.Failure("profile_unavailable");
        persist(copy().put("displayName", name));
    }

    private JSONObject copy() throws Exception { return new JSONObject(state.toString()); }
    private void persist(JSONObject next) throws Exception {
        String encoded = next.toString();
        if (encoded.getBytes(StandardCharsets.UTF_8).length > MAX_STORE_BYTES)
            throw new IllegalStateException("Garmin storage is full");
        storage.write(encoded);
        state = next;
    }

    private String workoutKey(String workoutId) throws Exception {
        if (workoutId == null || workoutId.isEmpty() || workoutId.length() > 128)
            throw new GarminCloudClient.Failure("upload_failed");
        for (int i = 0; i < workoutId.length(); i++) if (Character.isISOControl(workoutId.charAt(i)))
            throw new GarminCloudClient.Failure("upload_failed");
        return GarminCloudClient.sha256(workoutId.getBytes(StandardCharsets.UTF_8));
    }

    private int find(JSONArray receipts, String key) throws Exception {
        for (int i = 0; i < receipts.length(); i++) if (receipts.getJSONObject(i).getString("workout").equals(key)) return i;
        return -1;
    }

    boolean uncertain(String workout) throws Exception {
        JSONArray receipts = state.getJSONArray("receipts");
        int index = find(receipts, workoutKey(workout));
        return index >= 0 && receipts.getJSONObject(index).getString("status").equals("inflight");
    }

    /** Writes the uncertainty marker before the caller is permitted to start the POST. */
    GarminCloudClient.Outcome begin(String session, String workout, String sha, boolean retryUnknown) throws Exception {
        requireSession(session);
        if (sha == null || !sha.matches("[a-f0-9]{64}")) throw new GarminCloudClient.Failure("upload_failed");
        String key = workoutKey(workout);
        JSONObject next = copy();
        JSONArray receipts = next.getJSONArray("receipts");
        int index = find(receipts, key);
        if (index >= 0) {
            JSONObject entry = receipts.getJSONObject(index);
            if (!sha.equals(entry.getString("sha"))) throw new GarminCloudClient.Failure("content_changed");
            if (!session.equals(entry.getString("generation"))) throw new GarminCloudClient.Failure("session_changed");
            if (!entry.getString("status").equals("inflight"))
                return new GarminCloudClient.Outcome(entry.getString("status"), entry.optString("activityId", null));
            if (!retryUnknown) throw new GarminCloudClient.Failure("unknown_result");
            return null;
        }
        // Never evict even completed cross-generation guards: account identity is untrusted.
        if (receipts.length() >= MAX_RECEIPTS) throw new GarminCloudClient.Failure("receipt_limit");
        receipts.put(new JSONObject().put("workout", key).put("sha", sha)
            .put("status", "inflight").put("generation", session));
        persist(next);
        return null;
    }

    void complete(String workout, GarminCloudClient.Outcome result) throws Exception {
        JSONObject next = copy();
        JSONArray receipts = next.getJSONArray("receipts");
        int index = find(receipts, workoutKey(workout));
        if (index < 0 || !(result.status.equals("uploaded") || result.status.equals("duplicate")))
            throw new IllegalStateException("Missing Garmin upload marker");
        JSONObject entry = receipts.getJSONObject(index);
        if (!connected() || !sessionId().equals(entry.getString("generation")) || !entry.getString("status").equals("inflight"))
            throw new GarminCloudClient.Failure("session_changed");
        entry.put("status", result.status);
        if (result.activityId != null) entry.put("activityId", result.activityId);
        persist(next);
    }

    void definitelyFailed(String workout) throws Exception {
        JSONObject next = copy();
        JSONArray receipts = next.getJSONArray("receipts");
        int index = find(receipts, workoutKey(workout));
        if (index >= 0) {
            JSONObject entry = receipts.getJSONObject(index);
            if (!connected() || !sessionId().equals(entry.getString("generation"))) throw new GarminCloudClient.Failure("session_changed");
            if (entry.getString("status").equals("inflight")) receipts.remove(index);
        }
        persist(next);
    }

    static GarminCloudStore open(Context context) throws Exception { return new GarminCloudStore(new EncryptedStorage(context)); }

    static void saveLogin(Context context, String nonce, String token, String csrf) throws Exception {
        // An unreadable journal is never cleared to accept new credentials or a replay.
        open(context).finishLogin(nonce, token, csrf);
    }

    private static final class EncryptedStorage implements Storage {
        private static final String KEY_ALIAS = "opengym-garmin-cloud-v1";
        private static final byte[] AAD = "openGym Garmin cloud v1".getBytes(StandardCharsets.US_ASCII);
        private final AtomicFile file;

        EncryptedStorage(Context context) { file = new AtomicFile(new File(context.getNoBackupFilesDir(), "garmin-cloud.enc")); }

        private SecretKey key(boolean create) throws Exception {
            KeyStore keys = KeyStore.getInstance("AndroidKeyStore");
            keys.load(null);
            if (keys.containsAlias(KEY_ALIAS)) return (SecretKey) keys.getKey(KEY_ALIAS, null);
            if (!create) throw new IllegalStateException("Garmin key unavailable");
            KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
            generator.init(new KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256).build());
            return generator.generateKey();
        }

        @Override public String read() throws Exception {
            if (!file.getBaseFile().exists() && !new File(file.getBaseFile().getPath() + ".bak").exists()) return null;
            try (FileInputStream in = file.openRead(); ByteArrayOutputStream bytes = new ByteArrayOutputStream()) {
                byte[] chunk = new byte[4096];
                int count;
                while ((count = in.read(chunk)) != -1) {
                    if (bytes.size() + count > MAX_STORE_BYTES + 64) throw new IllegalStateException("Garmin storage too large");
                    bytes.write(chunk, 0, count);
                }
                byte[] encoded = bytes.toByteArray();
                if (encoded.length < 29 || encoded[0] != 1) throw new IllegalStateException("Invalid Garmin storage");
                Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
                cipher.init(Cipher.DECRYPT_MODE, key(false), new GCMParameterSpec(128, encoded, 1, 12));
                cipher.updateAAD(AAD);
                return new String(cipher.doFinal(encoded, 13, encoded.length - 13), StandardCharsets.UTF_8);
            }
        }

        @Override public void write(String value) throws Exception {
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE, key(true));
            cipher.updateAAD(AAD);
            byte[] iv = cipher.getIV(), encrypted = cipher.doFinal(value.getBytes(StandardCharsets.UTF_8));
            if (iv.length != 12) throw new IllegalStateException("Invalid Garmin encryption nonce");
            FileOutputStream out = null;
            try {
                out = file.startWrite();
                out.write(1);
                out.write(iv);
                out.write(encrypted);
                file.finishWrite(out);
            } catch (Exception e) { if (out != null) file.failWrite(out); throw e; }
        }

        @Override public void clear() throws Exception {
            KeyStore keys = KeyStore.getInstance("AndroidKeyStore");
            keys.load(null);
            keys.deleteEntry(KEY_ALIAS);
            file.delete();
            if (file.getBaseFile().exists() || new File(file.getBaseFile().getPath() + ".bak").exists())
                throw new IllegalStateException("Garmin storage could not be removed");
        }
    }
}
