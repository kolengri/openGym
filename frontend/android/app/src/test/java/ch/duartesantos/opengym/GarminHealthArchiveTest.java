package ch.duartesantos.opengym;

import org.json.JSONObject;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.FilterOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import static org.junit.Assert.*;

public class GarminHealthArchiveTest {
    private static final String OWNER = "a".repeat(64), OTHER = "b".repeat(64);
    private static final String DATE = "2024-02-29", METRIC = "sleep";
    @Rule public TemporaryFolder directory = new TemporaryFolder();

    enum Failure { NONE, READ, START, WRITE, FINISH, INTERRUPT, COMMITTED_INTERRUPT }
    static final class Interruption extends Error {}

    /** Recoverable real-file test adapter; Android AtomicFile itself is not a JVM implementation. */
    final class Disk implements GarminHealthArchive.Storage {
        Failure failure = Failure.NONE;
        int rollbacks, starts, opens;
        @Override public GarminHealthArchive.Entry open(String name) {
            opens++;
            Path base = directory.getRoot().toPath().resolve(name), backup = base.resolveSibling(name + ".bak");
            return new GarminHealthArchive.Entry() {
                @Override public InputStream openRead() throws Exception {
                    if (failure == Failure.READ) throw new IOException("Synthetic read failure");
                    if (Files.exists(backup)) {
                        Files.deleteIfExists(base);
                        Files.move(backup, base);
                    }
                    return Files.exists(base) ? Files.newInputStream(base) : null;
                }
                @Override public OutputStream startWrite() throws Exception {
                    starts++;
                    if (Files.exists(base)) Files.move(base, backup);
                    if (failure == Failure.START) throw new IOException("Synthetic start failure after backup");
                    return new FilterOutputStream(Files.newOutputStream(base)) {
                        @Override public void write(byte[] bytes) throws IOException {
                            if (failure == Failure.WRITE) {
                                out.write(bytes, 0, bytes.length / 2);
                                throw new IOException("Synthetic failure after partial replacement");
                            }
                            out.write(bytes);
                        }
                    };
                }
                @Override public void finishWrite(OutputStream stream) throws Exception {
                    stream.close();
                    if (failure == Failure.FINISH) throw new IOException("Synthetic finish failure");
                    if (failure == Failure.INTERRUPT) throw new Interruption();
                    Files.deleteIfExists(backup);
                    if (failure == Failure.COMMITTED_INTERRUPT) throw new Interruption();
                }
                @Override public void failWrite(OutputStream stream) throws Exception {
                    rollbacks++;
                    stream.close();
                    Files.deleteIfExists(base);
                    if (Files.exists(backup)) Files.move(backup, base);
                }
            };
        }
    }

    private String record(String date, String metric, String data) throws Exception {
        return new JSONObject().put("date", date).put("metric", metric).put("data", data).toString();
    }
    private String record(String data) throws Exception { return record(DATE, METRIC, data); }

    @Test public void readsLegacyPrivateNamesAndKeepsOwnersSeparateWithoutCloudSession() throws Exception {
        Disk disk = new Disk();
        String name = OWNER + "-" + DATE + "-" + METRIC + ".json";
        Files.write(directory.getRoot().toPath().resolve(name), record("legacy").getBytes(StandardCharsets.UTF_8));
        GarminHealthArchive archive = new GarminHealthArchive(disk);
        assertEquals("legacy", archive.read(OWNER, DATE, METRIC).getString("data"));
        assertNull(archive.read(OTHER, DATE, METRIC));
        archive.write(OTHER, DATE, METRIC, record("other"));
        assertEquals("legacy", archive.read(OWNER, DATE, METRIC).getString("data"));
        assertEquals("other", new GarminHealthArchive(disk).read(OTHER, DATE, METRIC).getString("data"));
    }

    @Test public void partialReplacementAndFinishFailuresRestorePreviousRecordOnReopen() throws Exception {
        for (Failure failure : new Failure[]{Failure.WRITE, Failure.FINISH}) {
            Disk disk = new Disk();
            GarminHealthArchive archive = new GarminHealthArchive(disk);
            archive.write(OWNER, DATE, METRIC, record("previous"));
            disk.failure = failure;
            assertThrows(IOException.class, () -> archive.write(OWNER, DATE, METRIC, record("replacement")));
            assertEquals(1, disk.rollbacks);
            disk.failure = Failure.NONE;
            assertEquals("previous", new GarminHealthArchive(disk).read(OWNER, DATE, METRIC).getString("data"));
        }
    }

    @Test public void interruptionOrStartFailureRecoversPreviousOrCompleteNewRecord() throws Exception {
        for (Failure failure : new Failure[]{Failure.START, Failure.INTERRUPT, Failure.COMMITTED_INTERRUPT}) {
            Disk disk = new Disk();
            GarminHealthArchive archive = new GarminHealthArchive(disk);
            archive.write(OWNER, DATE, METRIC, record("previous"));
            disk.failure = failure;
            if (failure == Failure.START)
                assertThrows(IOException.class, () -> archive.write(OWNER, DATE, METRIC, record("replacement")));
            else assertThrows(Interruption.class, () -> archive.write(OWNER, DATE, METRIC, record("replacement")));
            disk.failure = Failure.NONE;
            assertEquals(failure == Failure.COMMITTED_INTERRUPT ? "replacement" : "previous",
                new GarminHealthArchive(disk).read(OWNER, DATE, METRIC).getString("data"));
        }
    }

    @Test public void corruptOrUnreadableRecordsFailClosedAndRemainUnchanged() throws Exception {
        Disk disk = new Disk();
        GarminHealthArchive archive = new GarminHealthArchive(disk);
        Path base = directory.getRoot().toPath().resolve(OWNER + "-" + DATE + "-" + METRIC + ".json");
        for (String value : new String[]{"{broken", "[]", "null", record("wrong", METRIC, "data"), record("data") + " extra"}) {
            Files.write(base, value.getBytes(StandardCharsets.UTF_8));
            assertThrows(Exception.class, () -> archive.read(OWNER, DATE, METRIC));
            assertEquals(value, new String(Files.readAllBytes(base), StandardCharsets.UTF_8));
        }
        Files.write(base, new byte[]{(byte) 0xc3, (byte) 0x28});
        assertThrows(Exception.class, () -> archive.read(OWNER, DATE, METRIC));
        disk.failure = Failure.READ;
        assertThrows(IOException.class, () -> archive.read(OTHER, DATE, METRIC));
    }

    @Test public void rejectsInvalidPathsDatesAndUnknownMetricsBeforeStorageAccess() throws Exception {
        Disk disk = new Disk();
        GarminHealthArchive archive = new GarminHealthArchive(disk);
        String[][] invalid = {
            {"../" + OWNER, DATE, METRIC}, {OWNER.toUpperCase(), DATE, METRIC}, {null, DATE, METRIC},
            {OWNER, "2023-02-29", METRIC}, {OWNER, "2100-02-29", METRIC}, {OWNER, "1999-12-31", METRIC},
            {OWNER, "2101-01-01", METRIC}, {OWNER, "2024-02-29/..", METRIC}, {OWNER, null, METRIC},
            {OWNER, DATE, "../sleep"}, {OWNER, DATE, "Sleep"}, {OWNER, DATE, "unknown_metric"},
            {OWNER, DATE, "a".repeat(81)}, {OWNER, DATE, null}
        };
        for (String[] args : invalid) {
            assertEquals("invalid_metric", assertThrows(GarminCloudClient.Failure.class,
                () -> archive.read(args[0], args[1], args[2])).code);
        }
        assertEquals(0, disk.starts);
        assertEquals(0, disk.opens);
    }

    @Test public void supportsFullDateBoundsAndDigitContainingCatalogMetrics() throws Exception {
        Disk disk = new Disk();
        GarminHealthArchive archive = new GarminHealthArchive(disk);
        for (String date : new String[]{"2000-01-01", "2100-12-31"}) {
            for (String metric : new String[]{"spo2", "spo2_acclimation"}) {
                archive.write(OWNER, date, metric, record(date, metric, "archived"));
                assertEquals("archived", archive.read(OWNER, date, metric).getString("data"));
            }
        }
    }

    @Test public void rejectsMismatchedOrOversizedWritesBeforeBeginningReplacement() throws Exception {
        Disk disk = new Disk();
        GarminHealthArchive archive = new GarminHealthArchive(disk);
        archive.write(OWNER, DATE, METRIC, record("previous"));
        for (String value : new String[]{record(DATE, "stress", "wrong"), record("different", METRIC, "wrong"),
            "[]", record("é".repeat(GarminHealthArchive.MAX_RECORD_BYTES / 2)),
            record("x".repeat(GarminHealthArchive.MAX_RECORD_BYTES)), record("\ud800")}) {
            assertThrows(Exception.class, () -> archive.write(OWNER, DATE, METRIC, value));
        }
        assertEquals(1, disk.starts);
        assertEquals("previous", archive.read(OWNER, DATE, METRIC).getString("data"));
    }

    @Test public void byteLimitAppliesToExistingRecordsToo() throws Exception {
        Disk disk = new Disk();
        Path base = directory.getRoot().toPath().resolve(OWNER + "-" + DATE + "-" + METRIC + ".json");
        byte[] oversized = record("é".repeat(GarminHealthArchive.MAX_RECORD_BYTES / 2)).getBytes(StandardCharsets.UTF_8);
        assertTrue(oversized.length > GarminHealthArchive.MAX_RECORD_BYTES);
        Files.write(base, oversized);
        assertThrows(Exception.class, () -> new GarminHealthArchive(disk).read(OWNER, DATE, METRIC));
        assertArrayEquals(oversized, Files.readAllBytes(base));
    }
}
