package ch.duartesantos.opengym;

import static org.junit.Assert.*;
import static ch.duartesantos.opengym.RestAlert.CompletionGate.Outcome.*;
import org.junit.Test;

public class RestCompletionGateTest {
    @Test
    public void foregroundRestConsumesTheClaimBeforeTheSecondCallbackRunsInBackground() {
        RestAlert.CompletionGate gate = new RestAlert.CompletionGate();
        assertEquals(PAGE, gate.begin(1000, true, false, false));
        assertEquals(DUPLICATE, gate.begin(1000, false, false, false));
    }

    @Test
    public void foregroundWorkDefersUntilTheExplicitHandoffAfterHiding() {
        RestAlert.CompletionGate gate = new RestAlert.CompletionGate();
        assertEquals(PAGE, gate.begin(1000, true, true, false));
        assertEquals(NATIVE, gate.begin(1000, false, true, true));
        assertEquals(DUPLICATE, gate.begin(1000, false, true, false));
    }

    @Test
    public void hiddenPageHandoffCanSoundBeforeNativeVisibilityCatchesUp() {
        RestAlert.CompletionGate gate = new RestAlert.CompletionGate();
        assertEquals(PAGE, gate.begin(1000, true, true, false));
        assertEquals(NATIVE, gate.begin(1000, true, true, true));
        assertEquals(DUPLICATE, gate.begin(1000, false, true, false));
    }

    @Test
    public void pageChimeOrNativeAlarmConsumesTheWorkSignalExactlyOnce() {
        RestAlert.CompletionGate gate = new RestAlert.CompletionGate();
        assertTrue(gate.claim(1000));
        assertEquals(DUPLICATE, gate.begin(1000, false, true, true));
        assertEquals(NATIVE, gate.begin(2000, false, true, false));
        assertEquals(DUPLICATE, gate.begin(2000, false, true, true));
    }
}
