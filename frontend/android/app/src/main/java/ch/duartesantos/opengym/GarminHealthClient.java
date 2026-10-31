package ch.duartesantos.opengym;

import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.URI;
import java.net.URL;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import javax.net.ssl.HttpsURLConnection;

/** Fixed read-only health catalog, mapped from installed garminconnect 0.3.20. */
final class GarminHealthClient {
    static final int MAX_RESPONSE_BYTES = 2 * 1024 * 1024;
    static final int MAX_DEPTH = 32;
    static final int MAX_NODES = 100000;
    static final String PROFILE_URL = "https://connectapi.garmin.com/userprofile-service/socialProfile";
    private static final Map<String, Metric> METRICS = new LinkedHashMap<>();
    static final class Metric {
        final String id, label, template;
        Metric(String id, String label, String template) { this.id = id; this.label = label; this.template = template; }
    }
    static {
        add("daily_summary", "Daily summary", "/usersummary-service/v2/dailysummaries?startDate={date}&endDate={date}");
        add("weight", "Weight and body composition", "/weight-service/weight/dayview/{date}?includeAll=true");
        add("body_composition", "Body composition", "/weight-service/weight/dateRange?startDate={date}&endDate={date}");
        add("sleep", "Sleep", "/sleep-service/sleep/dailySleepData?date={date}&nonSleepBufferMinutes=60");
        add("naps", "Naps", "/sleep-service/sleep/naps/{date}?includeOverlaps=true");
        add("heart_rate", "Heart rate", "/wellness-service/wellness/dailyHeartRate/{name}?date={date}");
        add("resting_heart_rate", "Resting heart rate", "/userstats-service/wellness/daily/{name}?fromDate={date}&untilDate={date}&metricId=60");
        add("hrv", "Heart rate variability", "/hrv-service/hrv/{date}");
        add("stress", "Stress", "/wellness-service/wellness/dailyStress/{date}");
        add("body_battery", "Body Battery", "/wellness-service/wellness/bodyBattery/reports/daily?startDate={date}&endDate={date}");
        add("spo2", "Pulse oxygen saturation", "/wellness-service/wellness/daily/spo2/{date}");
        add("respiration", "Respiration", "/wellness-service/wellness/daily/respiration/{date}");
        add("hydration", "Hydration", "/usersummary-service/usersummary/hydration/allData/{date}");
        add("intensity_minutes", "Intensity minutes", "/wellness-service/wellness/daily/im/{date}");
        add("steps", "Steps", "/wellness-service/wellness/dailySummaryChart/{name}?date={date}");
        add("floors", "Floors", "/wellness-service/wellness/floorsChartData/daily/{date}");
        add("movement", "Movement", "/wellness-service/wellness/dailyMovement?calendarDate={date}");
        add("lifestyle", "Lifestyle log", "/lifestylelogging-service/dailyLog/{date}");
        add("training_readiness", "Training readiness", "/metrics-service/metrics/trainingreadiness/{date}");
        add("training_status", "Training status and load", "/metrics-service/metrics/trainingstatus/daily/{date}");
        add("training_load_balance", "Training load focus", "/metrics-service/metrics/trainingloadbalance/latest/{date}");
        add("fitness_age", "Fitness age", "/fitnessage-service/fitnessage/v2/{date}");
        add("max_metrics", "VO2 max", "/metrics-service/metrics/maxmet/daily/{date}/{date}");
        add("endurance_score", "Endurance score", "/metrics-service/metrics/endurancescore?calendarDate={date}");
        add("hill_score", "Hill score", "/metrics-service/metrics/hillscore?calendarDate={date}");
        add("blood_pressure", "Blood pressure", "/bloodpressure-service/bloodpressure/dayview/{date}");
        add("health_snapshot", "Health Snapshot summaries", "/wellnessactivity-service/activity/summary/{date}");
        add("ecg", "ECG daily summaries", "https://ghs.garmin.com/ghs/ecg/v1/ecg/daily?firstDay={date}&lastDay={date}");
        add("nutrition", "Daily nutrition totals", "/nutrition-service/calorie/summary/daily?startDate={date}&endDate={date}&currentDate={today}&isDataForReport=true");
        add("nutrition_food_log", "Nutrition food log", "/nutrition-service/food/logs/{date}?includeGoals=true&includeNutrition=true");
        add("nutrition_meals", "Nutrition meals", "/nutrition-service/meals/{date}");
        add("nutrition_settings", "Nutrition goals and settings", "/nutrition-service/settings/{date}");
        add("menstrual_day", "Menstrual health daily view", "/periodichealth-service/menstrualcycle/dayview/{date}?todayDate={today}");
        add("menstrual_summary", "Menstrual cycle summary", "/periodichealth-service/menstrualcycle/summary/{date}");
        add("menstrual_calendar", "Menstrual calendar", "/periodichealth-service/menstrualcycle/calendar/{date}/{date}");
        add("menstrual_last_confirmed", "Last confirmed menstrual cycle", "/periodichealth-service/menstrualcycle/lastconfirmed/{date}");
        add("glucose", "Glucose", "/biometric-service/biometric/glucose/{date}");
        add("heat_altitude_acclimation", "Heat and altitude acclimation", "/metrics-service/metrics/heataltitudeacclimation/daily/{date}/{date}");
        add("spo2_acclimation", "Pulse oxygen acclimation", "/wellness-service/wellness/daily/spo2acclimation/{date}");
        add("cycling_ability", "Cycling ability", "/metrics-service/metrics/cycling-ability?startDate={date}&endDate={date}&aggregation=DAILY");
        add("running_economy", "Running economy", "/metrics-service/metrics/runningeconomy/daily?startDate={date}&endDate={date}");
        add("running_tolerance", "Running tolerance", "/metrics-service/metrics/runningtolerance/stats?startDate={date}&endDate={date}&aggregation=daily");
        add("critical_swim_speed", "Critical swim speed", "/biometric-service/criticalSwimSpeed/range/{date}/{date}");
        add("biometric_stats", "Daily biometric statistics", "/biometric-service/stats?aggregation=daily&userFirstDay=monday&startDate={date}&endDate={date}");
        add("power_to_weight", "Power to weight", "/biometric-service/stats/powerToWeight/range/{date}/{date}?aggregation=daily");
        add("ftp_running", "Running threshold power", "/biometric-service/stats/functionalThresholdPower/range/{date}/{date}?sport=RUNNING&aggregation=daily&aggregationStrategy=LATEST");
        add("ftp_cycling", "Cycling threshold power", "/biometric-service/stats/functionalThresholdPower/range/{date}/{date}?sport=CYCLING&aggregation=daily&aggregationStrategy=LATEST");
        add("lactate_threshold_speed", "Lactate threshold speed", "/biometric-service/stats/lactateThresholdSpeed/range/{date}/{date}?sport=RUNNING&aggregation=daily&aggregationStrategy=LATEST");
        add("lactate_threshold_heart_rate", "Lactate threshold heart rate", "/biometric-service/stats/lactateThresholdHeartRate/range/{date}/{date}?sport=RUNNING&aggregation=daily&aggregationStrategy=LATEST");
        add("race_predictions", "Race predictions", "/metrics-service/metrics/racepredictions/daily/{name}?fromCalendarDate={date}&toCalendarDate={date}");
        add("jet_lag", "Jet lag guidance", "/jetlag-service/jetlag/status/daily/{date}");
        add("stamina_running", "Running stamina curve", "/metrics-service/metrics/stamina-curve/latest?calendarDate={date}&sportType=running");
        add("stamina_cycling", "Cycling stamina curve", "/metrics-service/metrics/stamina-curve/latest?calendarDate={date}&sportType=cycling");
        add("one_rep_max", "Strength one-rep maximum estimates", "/fitnessstats-service/vbt-stats/one-rep-max/current/{date}");
        add("power_curve_running", "Running power curve", "/fitnessstats-service/powerCurve?startDate={date}&endDate={date}&sport=running");
        add("power_curve_cycling", "Cycling power curve", "/fitnessstats-service/powerCurve?startDate={date}&endDate={date}&sport=cycling");
    }
    private static void add(String id, String label, String template) { METRICS.put(id, new Metric(id, label, template)); }

    interface Transport { Response get(String url, String token, String csrf) throws GarminCloudClient.Failure; }
    static final class Response {
        final int status;
        final String body;
        Response(int status, String body) { this.status = status; this.body = body; }
    }
    private final Transport transport;
    GarminHealthClient() { this(new Http()); }
    GarminHealthClient(Transport transport) { this.transport = transport; }

    static JSONArray catalog() throws Exception {
        JSONArray result = new JSONArray();
        for (Metric metric : METRICS.values()) result.put(new JSONObject().put("id", metric.id).put("label", metric.label));
        return result;
    }

    static String today() { return dateFormat().format(new Date()); }
    private static SimpleDateFormat dateFormat() {
        SimpleDateFormat format = new SimpleDateFormat("yyyy-MM-dd", Locale.US);
        format.setLenient(false);
        return format;
    }
    static void validateDate(String date, String today) throws GarminCloudClient.Failure {
        try {
            if (date == null || !date.matches("[0-9]{4}-[0-9]{2}-[0-9]{2}")) throw new Exception();
            SimpleDateFormat format = dateFormat();
            Date parsed = format.parse(date);
            Calendar last = Calendar.getInstance();
            last.setTime(format.parse(today));
            last.add(Calendar.DAY_OF_MONTH, 1);
            if (!format.format(parsed).equals(date) || parsed.before(format.parse("2000-01-01"))
                || parsed.after(last.getTime())) throw new Exception();
        } catch (Exception ignored) { throw new GarminCloudClient.Failure("invalid_date"); }
    }

    static boolean validDisplayName(String name) {
        if (name == null || name.trim().isEmpty() || name.length() > 256) return false;
        for (int i = 0; i < name.length(); i++) if (Character.isISOControl(name.charAt(i))) return false;
        return true;
    }
    static String encodePath(String value) {
        StringBuilder result = new StringBuilder();
        for (byte b : value.getBytes(StandardCharsets.UTF_8)) {
            int c = b & 255;
            if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')
                || c == '-' || c == '_' || c == '~') result.append((char) c);
            else result.append('%').append("0123456789ABCDEF".charAt(c >>> 4)).append("0123456789ABCDEF".charAt(c & 15));
        }
        return result.toString();
    }

    static String endpoint(String metric, String date, String today, String displayName) throws GarminCloudClient.Failure {
        Metric item = METRICS.get(metric);
        if (item == null) throw new GarminCloudClient.Failure("invalid_metric");
        validateDate(date, today);
        if (item.template.contains("{name}") && !validDisplayName(displayName)) throw new GarminCloudClient.Failure("profile_unavailable");
        String path = item.template.replace("{date}", date).replace("{today}", today)
            .replace("{name}", displayName == null ? "" : encodePath(displayName));
        String url = path.startsWith("https://") ? path : "https://connectapi.garmin.com" + path;
        if (!allowedUrl(url)) throw new GarminCloudClient.Failure("invalid_metric");
        return url;
    }

    /** No caller-provided URL, query keys, host, method or headers enter this transport. */
    static boolean allowedUrl(String value) {
        try {
            URI uri = new URI(value);
            return "https".equals(uri.getScheme()) && uri.getRawUserInfo() == null && uri.getPort() == -1
                && uri.getRawFragment() == null
                && ("connectapi.garmin.com".equals(uri.getHost())
                    || ("ghs.garmin.com".equals(uri.getHost()) && "/ghs/ecg/v1/ecg/daily".equals(uri.getPath())));
        } catch (Exception ignored) { return false; }
    }

    JSONObject read(GarminCloudStore store, String session, String date, String metric) throws Exception {
        store.requireSession(session);
        String currentDate = today();
        if (!METRICS.containsKey(metric)) throw new GarminCloudClient.Failure("invalid_metric");
        validateDate(date, currentDate);
        Metric item = METRICS.get(metric);
        String name = store.displayName();
        if (item.template.contains("{name}") && !validDisplayName(name)) {
            // Only this field is retained, encrypted and bound to the exact native session.
            Object profile = payload(transport.get(PROFILE_URL, store.token(), store.csrf()));
            if (!hasData(profile)) return envelope(metric, date, "unavailable");
            name = profile instanceof JSONObject ? ((JSONObject) profile).optString("displayName", null) : null;
            if (!validDisplayName(name)) throw new GarminCloudClient.Failure("profile_unavailable");
            store.cacheDisplayName(session, name);
        }
        String url = endpoint(metric, date, currentDate, name);
        Object data = payload(transport.get(url, store.token(), store.csrf()));
        Object clean = sanitize(data, 0, new int[]{0});
        JSONObject result = envelope(metric, date, hasData(clean) ? "available" : "unavailable");
        if (hasData(clean)) result.put("data", clean);
        return result;
    }

    static JSONObject envelope(String metric, String date, String status) throws Exception {
        // Invalid input cannot cause an unbounded/error-body echo through the bridge.
        return new JSONObject().put("metric", metric != null && metric.length() <= 64 ? metric : "")
            .put("date", date != null && date.matches("[0-9]{4}-[0-9]{2}-[0-9]{2}") ? date : "")
            .put("status", status);
    }
    static JSONObject error(String metric, String date, String code) throws Exception {
        return envelope(metric, date, "error").put("error", code);
    }

    static Object payload(Response response) throws GarminCloudClient.Failure {
        int status = response.status;
        if (status == 401) throw new GarminCloudClient.Failure("auth_required");
        if (status == 429) throw new GarminCloudClient.Failure("rate_limited");
        if (status == 403 || status == 404 || status == 204) return JSONObject.NULL;
        if (status < 200 || status >= 300) throw new GarminCloudClient.Failure("health_failed");
        String body = response.body;
        if (body == null || body.trim().isEmpty()) return JSONObject.NULL;
        if (body.length() > MAX_RESPONSE_BYTES || body.getBytes(StandardCharsets.UTF_8).length > MAX_RESPONSE_BYTES)
            throw new GarminCloudClient.Failure("response_too_large");
        preflight(body);
        try {
            JSONTokener reader = new JSONTokener(body);
            Object value = reader.nextValue();
            if (reader.nextClean() != 0 || !(value == JSONObject.NULL || value instanceof JSONObject || value instanceof JSONArray))
                throw new Exception();
            if (value instanceof JSONObject && ((JSONObject) value).optBoolean("privacyProtected", false))
                return JSONObject.NULL;
            return value;
        } catch (GarminCloudClient.Failure failure) { throw failure; }
        catch (Exception ignored) { throw new GarminCloudClient.Failure("invalid_response"); }
    }

    /** Bound nesting before org.json allocates recursively; bound total complexity as well as bytes. */
    static void preflight(String body) throws GarminCloudClient.Failure {
        int depth = 0, nodes = 0;
        boolean string = false, escaped = false;
        for (int i = 0; i < body.length(); i++) {
            char c = body.charAt(i);
            if (string) {
                if (escaped) escaped = false;
                else if (c == '\\') escaped = true;
                else if (c == '"') string = false;
            } else if (c == '"') { string = true; nodes++; }
            else if (c == '{' || c == '[') { if (++depth > MAX_DEPTH) throw new GarminCloudClient.Failure("response_too_complex"); nodes++; }
            else if (c == '}' || c == ']') { if (--depth < 0) throw new GarminCloudClient.Failure("invalid_response"); }
            else if (c == ',' || c == ':') nodes++;
            // org.json is lenient about comments/single quotes; reject these before its recursive parser.
            else if (c == '\'' || c == '/' || c == '(' || c == ')' || c == ';' || c == '=' || c == '>') throw new GarminCloudClient.Failure("invalid_response");
            if (nodes > MAX_NODES) throw new GarminCloudClient.Failure("response_too_complex");
        }
        if (string || depth != 0) throw new GarminCloudClient.Failure("invalid_response");
    }

    private static boolean privateKey(String key) {
        String normalized = key.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]", "");
        return normalized.contains("token") || normalized.contains("password") || normalized.contains("passwd")
            || normalized.contains("credential") || normalized.contains("authorization") || normalized.contains("authentication")
            || normalized.contains("cookie") || normalized.contains("csrf") || normalized.contains("secret")
            || normalized.contains("apikey") || normalized.contains("privatekey") || normalized.contains("accesskey")
            || (normalized.equals("session") || normalized.equals("sessionid") || normalized.equals("jsessionid")) || normalized.contains("oauth") || normalized.contains("jwt")
            || normalized.equals("headers") || normalized.equals("auth") || normalized.equals("username")
            || normalized.equals("email") || normalized.equals("displayname") || normalized.equals("fullname")
            || normalized.equals("profile") || normalized.equals("userprofile") || normalized.equals("socialprofile")
            || normalized.equals("account") || normalized.equals("personalinformation") || normalized.equals("usersettings");
    }
    static Object sanitize(Object value, int depth, int[] nodes) throws Exception {
        if (depth > MAX_DEPTH || ++nodes[0] > MAX_NODES) throw new GarminCloudClient.Failure("response_too_complex");
        if (value instanceof JSONObject) {
            JSONObject clean = new JSONObject();
            Iterator<String> keys = ((JSONObject) value).keys();
            while (keys.hasNext()) {
                String key = keys.next();
                if (!privateKey(key)) clean.put(key, sanitize(((JSONObject) value).get(key), depth + 1, nodes));
            }
            return clean;
        }
        if (value instanceof JSONArray) {
            JSONArray clean = new JSONArray();
            for (int i = 0; i < ((JSONArray) value).length(); i++) clean.put(sanitize(((JSONArray) value).get(i), depth + 1, nodes));
            return clean;
        }
        return value;
    }
    static boolean hasData(Object value) {
        if (value == null || value == JSONObject.NULL) return false;
        if (value instanceof JSONObject) {
            Iterator<String> keys = ((JSONObject) value).keys();
            while (keys.hasNext()) if (hasData(((JSONObject) value).opt(keys.next()))) return true;
            return false;
        }
        if (value instanceof JSONArray) {
            for (int i = 0; i < ((JSONArray) value).length(); i++) if (hasData(((JSONArray) value).opt(i))) return true;
            return false;
        }
        return !(value instanceof String) || !((String) value).trim().isEmpty();
    }

    static final class Http implements Transport {
        @Override public Response get(String url, String token, String csrf) throws GarminCloudClient.Failure {
            if (!allowedUrl(url)) throw new GarminCloudClient.Failure("invalid_metric");
            HttpsURLConnection connection = null;
            ScheduledFuture<?> deadline = null;
            try {
                Map<String, String> headers = GarminCloudClient.authHeaders(token, csrf);
                connection = (HttpsURLConnection) new URL(url).openConnection();
                HttpsURLConnection request = connection;
                deadline = GarminCloudClient.DEADLINES.schedule(request::disconnect, 60, TimeUnit.SECONDS);
                connection.setRequestMethod("GET");
                connection.setInstanceFollowRedirects(false);
                connection.setConnectTimeout(15000);
                connection.setReadTimeout(30000);
                connection.setUseCaches(false);
                for (Map.Entry<String, String> header : headers.entrySet()) connection.setRequestProperty(header.getKey(), header.getValue());
                int status = connection.getResponseCode();
                if (status < 200 || status >= 300 || status == 204) return new Response(status, null);
                if (connection.getContentLengthLong() > MAX_RESPONSE_BYTES) throw new GarminCloudClient.Failure("response_too_large");
                try (InputStream in = connection.getInputStream(); ByteArrayOutputStream bytes = new ByteArrayOutputStream()) {
                    byte[] buffer = new byte[8192];
                    int count;
                    while ((count = in.read(buffer)) != -1) {
                        if (bytes.size() + count > MAX_RESPONSE_BYTES) throw new GarminCloudClient.Failure("response_too_large");
                        bytes.write(buffer, 0, count);
                    }
                    String body;
                    try { body = StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                        .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes.toByteArray())).toString(); }
                    catch (CharacterCodingException ignored) { throw new GarminCloudClient.Failure("invalid_response"); }
                    return new Response(status, body);
                }
            } catch (GarminCloudClient.Failure failure) { throw failure; }
            catch (Exception ignored) { throw new GarminCloudClient.Failure("network_error"); }
            finally {
                if (deadline != null) deadline.cancel(false);
                if (connection != null) connection.disconnect();
            }
        }
    }
}
