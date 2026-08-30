// Lernansicht. Zeigt an und meldet Eingaben - entscheidet nichts.
// Alle Regeln (XP, Combo, Kartenwahl, Runden) liegen im Python-Core.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import theme
import "components"

Item {
    id: view

    // Weich hochzählende XP-Zahl: eine echte Property mit Behavior.
    property real xpAnzeige: lernen.xp
    Behavior on xpAnzeige {
        NumberAnimation { duration: Theme.dauerLangsam; easing.type: Easing.OutCubic }
    }

    readonly property color feedbackFarbe:
          lernen.feedbackArt === "richtig" ? Theme.success
        : lernen.feedbackArt === "falsch"  ? Theme.error
        : lernen.feedbackArt === "levelup" ? Theme.warning
        : Theme.textSecondary

    function eingabenSammeln() {
        var werte = []
        if (lernen.frageTyp === "triple") {
            for (var i = 0; i < tripleRepeater.count; i++) {
                var it = tripleRepeater.itemAt(i)
                if (it && it.istEingabe) werte.push(it.eingabeText)
            }
        } else if (lernen.frageTyp === "normal") {
            werte.push(normalFeld.text)
        }
        return werte
    }

    function pruefen() {
        if (lernen.gesperrt || !lernen.hatLernset) return
        var w = eingabenSammeln()
        if (w.length > 0) lernen.pruefe(w)
    }

    function ersteEingabeFokussieren() {
        if (lernen.frageTyp === "normal") {
            normalFeld.forceActiveFocus()
        } else if (lernen.frageTyp === "triple") {
            for (var i = 0; i < tripleRepeater.count; i++) {
                var it = tripleRepeater.itemAt(i)
                if (it && it.istEingabe) { it.fokussieren(); return }
            }
        }
    }

    Connections {
        target: lernen
        function onComboPuls() { comboBadge.pulsieren() }
        function onLevelUp() { levelUpAnim.restart() }
        function onFrageGeaendert() {
            kartenWechsel.restart()
            fokusTimer.restart()
        }
        function onFeedbackGeaendert() {
            if (lernen.gesperrt) weiterTimer.restart()
        }
    }

    Timer { id: fokusTimer; interval: 60; onTriggered: view.ersteEingabeFokussieren() }
    Timer {
        id: weiterTimer
        interval: lernen.feedbackArt === "falsch" ? 1900 : 1150
        onTriggered: lernen.weiter()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.abstandL
        spacing: Theme.abstandS

        // -- Kopfzeile --------------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.abstandM

            Text {
                Layout.fillWidth: true
                text: lernen.hatLernset ? lernen.lernsetName : "Kein Lernset gewählt"
                color: Theme.textPrimary
                font.pixelSize: Theme.schriftXl
                font.bold: true
                elide: Text.ElideRight
            }

            // Richtungsumschalter
            Row {
                spacing: 0
                Repeater {
                    model: einstellungen.richtungen
                    Rectangle {
                        required property string modelData
                        width: 52; height: 36
                        readonly property bool aktiv: modelData === einstellungen.richtung
                        color: aktiv ? Theme.surfaceElevated : "transparent"
                        border.color: Theme.border
                        border.width: 1
                        Behavior on color { ColorAnimation { duration: Theme.dauerSchnell } }
                        Text {
                            anchors.centerIn: parent
                            text: parent.modelData
                            font.pixelSize: 16
                            color: parent.aktiv ? Theme.textPrimary : Theme.textSecondary
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: einstellungen.setzeRichtung(parent.modelData)
                        }
                    }
                }
            }

            ComboBadge { id: comboBadge; wert: lernen.combo }
        }

        // -- XP-Zeile ---------------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.abstandS

            Text {
                text: "Level " + lernen.level
                color: Theme.textPrimary
                font.pixelSize: Theme.schriftM
                font.bold: true
                Layout.preferredWidth: 78
                // Level-Up: kurzes Aufleuchten
                SequentialAnimation {
                    id: levelUpAnim
                    ColorAnimation { target: parent; property: "color"; to: Theme.warning; duration: 160 }
                    NumberAnimation { target: parent; property: "scale"; to: 1.22; duration: 160; easing.type: Easing.OutBack }
                    NumberAnimation { target: parent; property: "scale"; to: 1.0; duration: 260; easing.type: Easing.OutCubic }
                    ColorAnimation { target: parent; property: "color"; to: Theme.textPrimary; duration: 420 }
                }
            }
            ProgressTrack {
                Layout.fillWidth: true
                anteil: lernen.levelAnteil
                fuellFarbe: Theme.primary
            }
            Text {
                text: lernen.maxLevel
                      ? Math.round(view.xpAnzeige) + " XP"
                      : Math.round(view.xpAnzeige) + " / " + lernen.xpBisLevel + " XP"
                color: Theme.textSecondary
                font.pixelSize: Theme.schriftS
                horizontalAlignment: Text.AlignRight
                Layout.preferredWidth: 130
            }
        }

        // -- Karte ------------------------------------------------------------
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Rectangle {
                id: karte
                anchors.centerIn: parent
                width: Math.min(parent.width, 660)
                // Die Karte richtet sich nach ihrem Inhalt, nicht nach der
                // Fensterhoehe - sonst steht sie bei kurzen Fragen leer herum.
                readonly property real inhaltsHoehe:
                      normalBlock.visible ? normalBlock.implicitHeight
                    : tripleBlock.visible ? tripleBlock.implicitHeight
                    : fertigBlock.visible ? fertigBlock.implicitHeight
                    : 60
                height: Math.min(parent.height, Math.max(200, inhaltsHoehe + 2 * Theme.abstandXl))
                radius: Theme.radiusGross
                color: Theme.surface
                border.width: 1
                border.color: lernen.feedbackArt === "richtig" || lernen.feedbackArt === "levelup"
                                ? Theme.success
                            : lernen.feedbackArt === "falsch" ? Theme.error
                            : Theme.border
                Behavior on border.color { ColorAnimation { duration: Theme.dauerNormal } }
                Behavior on height { NumberAnimation { duration: Theme.dauerNormal; easing.type: Easing.OutCubic } }

                // Kartenwechsel als 3D-Flip um die Y-Achse.
                transform: Rotation {
                    id: flip
                    origin.x: karte.width / 2
                    origin.y: karte.height / 2
                    axis { x: 0; y: 1; z: 0 }
                    angle: 0
                }
                SequentialAnimation {
                    id: kartenWechsel
                    NumberAnimation { target: flip; property: "angle"; to: 84; duration: 130; easing.type: Easing.InCubic }
                    NumberAnimation { target: flip; property: "angle"; to: 0;  duration: 200; easing.type: Easing.OutCubic }
                }

                // ---- Leerzustand
                Text {
                    anchors.centerIn: parent
                    visible: lernen.frageTyp === "leer"
                    text: "Wähle links ein Lernset"
                    color: Theme.textSecondary
                    font.pixelSize: Theme.schriftL
                }

                // ---- Normale Karte
                ColumnLayout {
                    id: normalBlock
                    anchors.centerIn: parent
                    width: parent.width - 2 * Theme.abstandXl
                    visible: lernen.frageTyp === "normal"
                    spacing: Theme.abstandL

                    Text {
                        Layout.fillWidth: true
                        text: lernen.frageText
                        color: Theme.textPrimary
                        font.pixelSize: Theme.schriftHero
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                        maximumLineCount: 3
                        elide: Text.ElideRight
                    }
                    Text {
                        Layout.fillWidth: true
                        visible: lernen.rueckwaerts
                        text: "rückwärts"
                        color: Theme.textSecondary
                        font.pixelSize: Theme.schriftXs
                        horizontalAlignment: Text.AlignHCenter
                    }
                    AnswerField {
                        id: normalFeld
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: 320
                        readOnly: lernen.gesperrt
                        falschMarkiert: lernen.feedbackArt === "falsch"
                        placeholderText: "Antwort"
                        onAccepted: view.pruefen()
                    }
                }

                // ---- Triple-Karte
                ColumnLayout {
                    id: tripleBlock
                    anchors.centerIn: parent
                    width: parent.width - 2 * Theme.abstandL
                    visible: lernen.frageTyp === "triple"
                    spacing: Theme.abstandM

                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: "Alle drei Formen"
                        color: Theme.textSecondary
                        font.pixelSize: Theme.schriftS
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.maximumWidth: 3 * 152 + 2 * Theme.abstandS
                        Layout.alignment: Qt.AlignHCenter
                        spacing: Theme.abstandS
                        Repeater {
                            id: tripleRepeater
                            model: lernen.slots
                            delegate: Item {
                                id: slot
                                required property var modelData
                                required property int index
                                readonly property bool istEingabe: modelData.eingabe
                                property alias eingabeText: slotFeld.text
                                function fokussieren() { if (istEingabe) slotFeld.forceActiveFocus() }

                                // Mitschrumpfen, sonst läuft die dritte Spalte
                                // in schmalen Fenstern aus der Karte heraus.
                                Layout.fillWidth: true
                                Layout.minimumWidth: 84
                                Layout.maximumWidth: 152
                                implicitWidth: 152
                                implicitHeight: 58

                                Rectangle {
                                    anchors.fill: parent
                                    visible: !slot.istEingabe
                                    radius: Theme.radiusMittel
                                    color: Theme.surfaceElevated
                                    border.width: 1
                                    border.color: Theme.border
                                    Text {
                                        anchors.centerIn: parent
                                        width: parent.width - 12
                                        text: slot.modelData.text
                                        color: Theme.textPrimary
                                        font.pixelSize: Theme.schriftL
                                        font.bold: true
                                        horizontalAlignment: Text.AlignHCenter
                                        elide: Text.ElideRight
                                    }
                                }
                                AnswerField {
                                    id: slotFeld
                                    anchors.fill: parent
                                    visible: slot.istEingabe
                                    readOnly: lernen.gesperrt
                                    falschMarkiert: lernen.feedbackArt === "falsch"
                                    onAccepted: view.pruefen()
                                }
                            }
                        }
                    }
                }

                // ---- Abschlussstatistik
                ColumnLayout {
                    id: fertigBlock
                    anchors.centerIn: parent
                    width: parent.width - 2 * Theme.abstandL
                    visible: lernen.frageTyp === "fertig"
                    spacing: Theme.abstandS

                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: "Alles gelernt"
                        color: Theme.warning
                        font.pixelSize: Theme.schriftXl
                        font.bold: true
                    }
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: (lernen.statistik.accuracy || 0) + "% richtig   ·   "
                              + (lernen.statistik.richtig || 0) + " richtig · "
                              + (lernen.statistik.falsch || 0) + " falsch"
                        color: Theme.textSecondary
                        font.pixelSize: Theme.schriftM
                    }
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: "Level " + (lernen.statistik.level || 1) + "   ·   "
                              + (lernen.statistik.xp || 0) + " XP   ·   beste Combo "
                              + (lernen.statistik.bestCombo || 0) + "   ·   "
                              + (lernen.statistik.runden || 1) + " Runden"
                        color: Theme.textSecondary
                        font.pixelSize: Theme.schriftS
                    }
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        visible: (lernen.statistik.schwerste || []).length > 0
                        text: "Schwierigste Karten"
                        color: Theme.textSecondary
                        font.pixelSize: Theme.schriftXs
                        topPadding: Theme.abstandXs
                    }
                    Repeater {
                        model: lernen.statistik.schwerste || []
                        delegate: Text {
                            required property var modelData
                            Layout.alignment: Qt.AlignHCenter
                            text: modelData.frage + "  —  " + modelData.anzahl + "× falsch"
                            color: Theme.textSecondary
                            font.pixelSize: Theme.schriftXs
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }

        // -- Feedback ---------------------------------------------------------
        Text {
            Layout.fillWidth: true
            Layout.preferredHeight: 22
            text: lernen.feedbackText
            color: view.feedbackFarbe
            font.pixelSize: Theme.schriftM
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            opacity: lernen.feedbackText === "" ? 0 : 1
            Behavior on opacity { NumberAnimation { duration: Theme.dauerSchnell } }
        }

        // -- Aktionen ---------------------------------------------------------
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: Theme.abstandS

            PrimaryButton {
                text: "Prüfen"
                visible: lernen.frageTyp === "normal" || lernen.frageTyp === "triple"
                enabled: !lernen.gesperrt
                onClicked: view.pruefen()
            }
            PrimaryButton {
                text: "Neu starten"
                visible: lernen.frageTyp === "fertig"
                onClicked: lernen.neustart()
            }
            PrimaryButton {
                text: "Fortschritt löschen"
                sekundaer: true
                implicitWidth: 170
                implicitHeight: 40
                enabled: lernen.hatLernset
                onClicked: loeschBestaetigung.open()
            }
        }

        // -- Gesamtfortschritt ------------------------------------------------
        ProgressTrack {
            Layout.fillWidth: true
            Layout.topMargin: Theme.abstandXs
            dicke: 8
            anteil: lernen.anteil
            fuellFarbe: Theme.success
        }
        Text {
            Layout.fillWidth: true
            text: lernen.hatLernset
                  ? lernen.gelernt + " / " + lernen.gesamt + " gelernt   ·   Runde "
                    + lernen.runde + "   ·   beste Combo " + lernen.bestCombo
                  : ""
            color: Theme.textSecondary
            font.pixelSize: Theme.schriftS
            horizontalAlignment: Text.AlignHCenter
        }
    }

    Dialog {
        id: loeschBestaetigung
        anchors.centerIn: Overlay.overlay
        modal: true
        title: "Fortschritt löschen?"
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: lernen.fortschrittLoeschen()
        background: Rectangle {
            color: Theme.surface; radius: Theme.radiusMittel
            border.color: Theme.border; border.width: 1
        }
        contentItem: Text {
            text: "XP, Level und Streaks dieses Lernsets werden zurückgesetzt.\n"
                  + "Die beste Combo bleibt als Rekord erhalten."
            color: Theme.textPrimary
            font.pixelSize: Theme.schriftM
            wrapMode: Text.WordWrap
        }
    }
}
