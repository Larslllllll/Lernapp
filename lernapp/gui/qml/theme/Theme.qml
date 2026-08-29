// Zentrale Design-Tokens. Einzige Quelle fuer Farben, Radien und Zeiten.
// Dark und Light teilen dieselbe semantische Struktur - es wechseln nur die
// Werte, nie die Namen.
pragma Singleton
import QtQuick

QtObject {
    id: theme

    // Wird von Main.qml aus dem SettingsViewModel gesetzt.
    property bool dark: true

    // -- Flaechen -------------------------------------------------------------
    readonly property color background:      dark ? "#0f1115" : "#f4f5f8"
    readonly property color surface:         dark ? "#171a21" : "#ffffff"
    readonly property color surfaceElevated: dark ? "#1e222b" : "#ffffff"
    readonly property color border:          dark ? "#272c38" : "#dfe3ec"

    // -- Marke / Aktionen -----------------------------------------------------
    readonly property color primary:         dark ? "#5b8cff" : "#2f6bf0"
    readonly property color primaryHover:    dark ? "#7aa1ff" : "#1f56d0"
    readonly property color onPrimary:       dark ? "#0b1020" : "#ffffff"
    readonly property color accent:          dark ? "#c792ff" : "#7c3fd0"

    // -- Semantik -------------------------------------------------------------
    readonly property color success:         dark ? "#3ddc84" : "#12a150"
    readonly property color error:           dark ? "#ff5c5c" : "#d92d20"
    readonly property color warning:         dark ? "#ffc857" : "#b25e00"

    // -- Text -----------------------------------------------------------------
    readonly property color textPrimary:     dark ? "#e8eaf0" : "#12141a"
    readonly property color textSecondary:   dark ? "#8b93a7" : "#5b6376"
    readonly property color textDisabled:    dark ? "#525a6c" : "#9aa1b1"

    // -- Combo-Stufen (nur Darstellung, die Schwellen kennt der Core) ---------
    readonly property color comboHoch:       dark ? "#ffc857" : "#c98a00"
    readonly property color comboMittel:     dark ? "#ff7a3d" : "#e05d1a"
    readonly property color comboNiedrig:    primary

    // -- Form -----------------------------------------------------------------
    readonly property int radiusKlein: 8
    readonly property int radiusMittel: 12
    readonly property int radiusGross: 18
    readonly property int radiusRund: 999

    // -- Abstaende ------------------------------------------------------------
    readonly property int abstandXs: 6
    readonly property int abstandS: 10
    readonly property int abstandM: 16
    readonly property int abstandL: 26
    readonly property int abstandXl: 40

    // -- Zeiten ---------------------------------------------------------------
    readonly property int dauerSchnell: 150
    readonly property int dauerNormal: 220
    readonly property int dauerLangsam: 420

    // -- Schrift --------------------------------------------------------------
    readonly property int schriftXs: 11
    readonly property int schriftS: 12
    readonly property int schriftM: 14
    readonly property int schriftL: 19
    readonly property int schriftXl: 28
    readonly property int schriftHero: 34
}
