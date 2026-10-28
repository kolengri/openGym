package ch.duartesantos.opengym;

/** The Garmin companion installs only its own checked fork updates. */
final class FlavorPlugins {
    private FlavorPlugins() {}

    static void register(MainActivity activity) {
        activity.registerFlavorPlugin(InstallPlugin.class);
    }
}
