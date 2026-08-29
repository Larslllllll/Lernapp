// Hauptfenster: Seitenleiste + Lernansicht.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import theme

ApplicationWindow {
    id: fenster
    width: einstellungen.fensterBreite
    height: einstellungen.fensterHoehe
    minimumWidth: 720
    minimumHeight: 560
    visible: true
    title: "LernApp"
    color: Theme.background

    // Einzige Stelle, an der das Theme umgeschaltet wird.
    Binding {
        target: Theme
        property: "dark"
        value: einstellungen.dark
    }

    onWidthChanged: groesseTimer.restart()
    onHeightChanged: groesseTimer.restart()
    Timer {
        id: groesseTimer
        interval: 600
        onTriggered: einstellungen.merkeFenster(fenster.width, fenster.height)
    }

    // -- Tastatur (global) ----------------------------------------------------
    Shortcut { sequence: "Ctrl+N"; onActivated: dialog.oeffnenNeu(sets.ordnerNamen[0] || "") }
    Shortcut { sequence: "Ctrl+E"; onActivated: if (lernen.lernsetId) dialog.oeffnenBearbeiten(lernen.lernsetId) }
    Shortcut { sequence: "Ctrl+D"; onActivated: einstellungen.themeUmschalten() }
    Shortcut { sequence: "Ctrl+R"; onActivated: if (lernen.hatLernset) lernen.neustart() }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        SetsView {
            id: seitenleiste
            Layout.preferredWidth: 268
            Layout.minimumWidth: 220
            Layout.fillHeight: true
            onBearbeiten: function(lernsetId) { dialog.oeffnenBearbeiten(lernsetId) }
            onNeuAnlegen: function(ordner) { dialog.oeffnenNeu(ordner) }
        }

        Rectangle {
            Layout.preferredWidth: 1
            Layout.fillHeight: true
            color: Theme.border
        }

        LearnView {
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }

    LernsetDialog {
        id: dialog
        anchors.centerIn: Overlay.overlay
        onGespeichert: function(lernsetId) {
            sets.aktualisiere()
            if (lernen.lernsetId === lernsetId)
                lernen.lernsetNeuLaden()
        }
    }

    // Fehlermeldungen aus den ViewModels sichtbar machen.
    Connections {
        target: sets
        function onFehler(text) { hinweis.zeige(text) }
    }

    Rectangle {
        id: hinweis
        function zeige(text) { hinweisText.text = text; einblenden.restart() }

        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.abstandL
        width: hinweisText.implicitWidth + 2 * Theme.abstandL
        height: 44
        radius: Theme.radiusRund
        color: Theme.surfaceElevated
        border.width: 1
        border.color: Theme.error
        opacity: 0

        Text {
            id: hinweisText
            anchors.centerIn: parent
            color: Theme.textPrimary
            font.pixelSize: Theme.schriftM
        }
        SequentialAnimation {
            id: einblenden
            NumberAnimation { target: hinweis; property: "opacity"; to: 1; duration: Theme.dauerSchnell }
            PauseAnimation { duration: 2600 }
            NumberAnimation { target: hinweis; property: "opacity"; to: 0; duration: Theme.dauerNormal }
        }
    }
}
