package ch.duartesantos.opengym;

import android.content.Context;
import android.system.ErrnoException;
import android.system.Os;
import android.system.OsConstants;
import android.util.AtomicFile;
import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.CharBuffer;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Locale;

/** Private per-owner archive, independent of cloud credentials and available offline. Call on IO. */
final class GarminHealthArchive {
    static final int MAX_RECORD_BYTES = 3 * 1024 * 1024;

    interface Storage { Entry open(String name) throws Exception; }
    interface Entry {
        // Null means absent; every other read failure must throw.
        InputStream openRead() throws Exception;
        OutputStream startWrite() throws Exception;
        void finishWrite(OutputStream stream) throws Exception;
        void failWrite(OutputStream stream) throws Exception;
    }

    private final Storage storage;
    GarminHealthArchive(Storage storage) { this.storage = storage; }

    static GarminHealthArchive open(Context context) {
        File directory = new File(context.getFilesDir(), "opengym-garmin-health");
        return new GarminHealthArchive(name -> new AndroidEntry(new File(directory, name)));
    }

    JSONObject read(String ownerKey, String date, String metric) throws Exception {
        Entry entry = storage.open(name(ownerKey, date, metric));
        try (InputStream input = entry.openRead()) {
            if (input == null) return null;
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            byte[] buffer = new byte[8192];
            int count;
            while ((count = input.read(buffer)) != -1) {
                if (bytes.size() + count > MAX_RECORD_BYTES) throw new Exception("storage_error");
                bytes.write(buffer, 0, count);
            }
            String value = StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes.toByteArray())).toString();
            return record(value, date, metric);
        }
    }

    void write(String ownerKey, String date, String metric, String value) throws Exception {
        String name = name(ownerKey, date, metric);
        record(value, date, metric);
        ByteBuffer encoded = StandardCharsets.UTF_8.newEncoder().onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT).encode(CharBuffer.wrap(value));
        if (encoded.remaining() > MAX_RECORD_BYTES) throw new Exception("storage_error");
        byte[] bytes = new byte[encoded.remaining()];
        encoded.get(bytes);
        Entry entry = storage.open(name);
        OutputStream stream = null;
        try {
            stream = entry.startWrite();
            stream.write(bytes);
            entry.finishWrite(stream);
        } catch (Exception failure) {
            if (stream != null) {
                try { entry.failWrite(stream); }
                catch (Exception rollbackFailure) { failure.addSuppressed(rollbackFailure); }
            }
            throw failure;
        }
    }

    private static JSONObject record(String value, String date, String metric) throws Exception {
        if (value == null || value.length() > MAX_RECORD_BYTES) throw new Exception("storage_error");
        JSONTokener parser = new JSONTokener(value);
        Object parsed = parser.nextValue();
        if (!(parsed instanceof JSONObject) || parser.nextClean() != 0) throw new Exception("storage_error");
        JSONObject object = (JSONObject) parsed;
        if (!date.equals(object.opt("date")) || !metric.equals(object.opt("metric"))) throw new Exception("storage_error");
        return object;
    }

    private static String name(String ownerKey, String date, String metric) throws Exception {
        boolean known = false;
        if (metric != null && metric.matches("[a-z][a-z0-9_]{0,79}")) {
            JSONArray catalog = GarminHealthClient.catalog();
            for (int i = 0; i < catalog.length(); i++) {
                if (metric.equals(catalog.getJSONObject(i).getString("id"))) { known = true; break; }
            }
        }
        if (ownerKey == null || !ownerKey.matches("[a-f0-9]{64}") || !known || !validDate(date))
            throw new GarminCloudClient.Failure("invalid_metric");
        return ownerKey + "-" + date + "-" + metric + ".json";
    }

    private static boolean validDate(String date) {
        if (date == null || !date.matches("(?:20[0-9]{2}|2100)-[0-9]{2}-[0-9]{2}")) return false;
        SimpleDateFormat format = new SimpleDateFormat("yyyy-MM-dd", Locale.US);
        format.setLenient(false);
        try { return date.equals(format.format(format.parse(date))); }
        catch (Exception ignored) { return false; }
    }

    private static final class AndroidEntry implements Entry {
        private final AtomicFile file;
        AndroidEntry(File base) { file = new AtomicFile(base); }

        @Override public InputStream openRead() throws Exception {
            try { return file.openRead(); }
            catch (FileNotFoundException missing) {
                // FileNotFoundException also covers permission and recovery failures.
                if (exists(file.getBaseFile()) || exists(new File(file.getBaseFile().getPath() + ".bak"))) throw missing;
                return null;
            }
        }
        private static boolean exists(File path) throws Exception {
            try { Os.stat(path.getPath()); return true; }
            catch (ErrnoException failure) {
                if (failure.errno == OsConstants.ENOENT) return false;
                throw failure;
            }
        }
        @Override public OutputStream startWrite() throws Exception { return file.startWrite(); }
        @Override public void finishWrite(OutputStream stream) { file.finishWrite((FileOutputStream) stream); }
        @Override public void failWrite(OutputStream stream) { file.failWrite((FileOutputStream) stream); }
    }
}
