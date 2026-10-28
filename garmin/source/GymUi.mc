import Toybox.WatchUi;

module GymUi {
    function string(id) { return WatchUi.loadResource(id); }
    function message(value) {
        if (value == null) { return ""; }
        if (value.equals("Storage recovery failed. Keep app data.")) { return string(Rez.Strings.StorageRecovery); }
        if (value.equals("Storage full. Reconnect phone.")) { return string(Rez.Strings.StorageFull); }
        if (value.equals("Recording interrupted")) { return string(Rez.Strings.RecordingInterrupted); }
        if (value.equals("Recording off")) { return string(Rez.Strings.RecordingOff); }
        if (value.equals("Recording failed")) { return string(Rez.Strings.RecordingFailed); }
        if (value.equals("Recording FIT")) { return string(Rez.Strings.RecordingFit); }
        if (value.equals("Recording unavailable")) { return string(Rez.Strings.RecordingUnavailable); }
        if (value.equals("Recording paused")) { return string(Rez.Strings.RecordingPaused); }
        if (value.equals("Recording error")) { return string(Rez.Strings.RecordingError); }
        if (value.equals("Save pending: storage error")) { return string(Rez.Strings.SavePending); }
        if (value.equals("FIT discarded")) { return string(Rez.Strings.FitDiscarded); }
        if (value.equals("FIT saved")) { return string(Rez.Strings.FitSaved); }
        if (value.equals("FIT completion failed")) { return string(Rez.Strings.FitFailed); }
        if (value.equals("FIT completion interrupted")) { return string(Rez.Strings.FitInterrupted); }
        if (value.equals("Invalid phone message")) { return string(Rez.Strings.InvalidMessage); }
        if (value.equals("Workout too large. Reduce sets on phone.")) { return string(Rez.Strings.WorkoutTooLarge); }
        if (value.equals("Invalid workout. Check phone.")) { return string(Rez.Strings.InvalidWorkout); }
        if (value.equals("Start a workout on phone")) { return string(Rez.Strings.StartWorkoutPhone); }
        if (value.equals("Sync queue full. Reconnect phone.")) { return string(Rez.Strings.QueueFull); }
        if (value.equals("Timed set unavailable")) { return string(Rez.Strings.TimedUnavailable); }
        if (value.equals("Set unavailable")) { return string(Rez.Strings.SetUnavailable); }
        if (value.equals("Set already started")) { return string(Rez.Strings.AlreadyStarted); }
        if (value.equals("Resume workout first")) { return string(Rez.Strings.ResumeFirst); }
        if (value.equals("Skip rest from menu first")) { return string(Rez.Strings.SkipRestFirst); }
        if (value.equals("Exercise complete. Press DOWN.")) { return string(Rez.Strings.ExerciseComplete); }
        if (value.equals("Unsupported set. Use phone.")) { return string(Rez.Strings.UnsupportedSet); }
        if (value.equals("Timer just started")) { return string(Rez.Strings.TimerStarted); }
        return value;
    }
    function side(value) {
        return string(value.equals("L") ? Rez.Strings.Left : Rez.Strings.Right);
    }
    function unit(value) {
        return string(value.equals("kg") ? Rez.Strings.Kilograms : Rez.Strings.Pounds);
    }
}
