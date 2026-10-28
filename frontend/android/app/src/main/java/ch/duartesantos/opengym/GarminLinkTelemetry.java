package ch.duartesantos.opengym;

import org.json.JSONObject;

/** Transient diagnostics only; never advances the journal or acknowledges a command. */
final class GarminLinkTelemetry {
    private long lastMessageAt, confirmedAt, reportedSeq = -1;
    private String reportedWid, confirmedWid;
    private int watchPending = -1;

    void reset() { lastMessageAt = confirmedAt = 0; reportedSeq = -1; reportedWid = confirmedWid = null; watchPending = -1; }

    void receive(JSONObject message, JSONObject target, int phonePending, long now) {
        lastMessageAt = now;
        if (!"hello".equals(message.optString("kind"))) return;
        boolean complete = message.has("seq") && message.has("wid") && message.has("pending");
        reportedSeq = complete ? message.optLong("seq", -1) : -1;
        reportedWid = message.isNull("wid") ? null : message.optString("wid", null);
        watchPending = message.optInt("pending", -1);
        if (matches(target) && phonePending == 0 && watchPending == 0) { confirmedAt = now; confirmedWid = reportedWid; }
    }

    private boolean sameWorkout(JSONObject target) {
        if (target == null) return false;
        String wanted = target.isNull("wid") ? null : target.optString("wid", null);
        return wanted == null ? reportedWid == null : wanted.equals(reportedWid);
    }

    private boolean matches(JSONObject target) {
        return target != null && reportedSeq >= 0 && reportedSeq == target.optLong("seq", -2) && sameWorkout(target);
    }

    JSONObject status(JSONObject target, int phonePending) throws Exception {
        boolean same = sameWorkout(target);
        String wanted = target == null || target.isNull("wid") ? null : target.optString("wid", null);
        boolean confirmedWorkout = wanted == null ? confirmedWid == null : wanted.equals(confirmedWid);
        return new JSONObject().put("lastMessageAt", lastMessageAt)
            .put("lastConfirmedAt", confirmedWorkout ? confirmedAt : 0)
            .put("snapshotConfirmed", matches(target) && phonePending == 0 && watchPending == 0)
            .put("watchPending", same && reportedSeq >= 0 ? watchPending : -1)
            .put("phonePending", phonePending)
            .put("workoutId", target == null ? JSONObject.NULL : target.opt("wid"));
    }
}
