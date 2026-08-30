// Ein eigenes Lernset im Marktplatz einreichen.
//
// Stellt nur dar. Sperrliste, Anmeldung und Pull Request macht das ViewModel;
// hier steht keine Regel und keine Schwelle.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import theme
import "components"

Dialog {
    id: dlg
    modal: true
    title: "Veröffentlichen"
    width: 520
    closePolicy: Popup.CloseOnEscape

    property string lernsetId: ""
    property var pruefung: ({ ok: false, grund: "" })

    function oeffnen(id) {
        lernsetId = id
        pruefung = publizieren.pruefe(id)
        open()
    }

    background: Rectangle {
        color: Theme.surface
        radius: Theme.radiusGross
        border.width: 1
        border.color: Theme.border
    }

    header: ColumnLayout {
        spacing: 2
        Text {
            Layout.margins: Theme.abstandL
            Layout.bottomMargin: 0
            text: "Lernset veröffentlichen"
            color: Theme.textPrimary
            font.pixelSize: Theme.schriftL
            font.bold: true
        }
        Text {
            Layout.leftMargin: Theme.abstandL
            Layout.rightMargin: Theme.abstandL
            text: dlg.pruefung.ok
                  ? dlg.pruefung.name + " · " + dlg.pruefung.fach
                    + " · " + dlg.pruefung.karten + " Karten"
                  : "Prüfung nicht bestanden"
            color: Theme.textSecondary
            font.pixelSize: Theme.schriftS
        }
    }

    contentItem: ColumnLayout {
        spacing: Theme.abstandM

        // -- Fall 1: die Sperrliste hat angeschlagen --------------------------
        Rectangle {
            Layout.fillWidth: true
            Layout.margins: Theme.abstandL
            Layout.topMargin: Theme.abstandM
            visible: !dlg.pruefung.ok
            // Erst die Breite, dann die Hoehe: `anchors.fill` plus
            // `implicitHeight` waere zirkulaer, und der Text stuende
            // ueber den Rand hinaus.
            implicitHeight: gesperrtText.height + 2 * Theme.abstandM
            radius: Theme.radiusMittel
            color: "transparent"
            border.width: 1
            border.color: Theme.error

            Text {
                id: gesperrtText
                x: Theme.abstandM
                y: Theme.abstandM
                width: parent.width - 2 * Theme.abstandM
                text: dlg.pruefung.grund
                color: Theme.textPrimary
                font.pixelSize: Theme.schriftS
                wrapMode: Text.WordWrap
            }
        }

        // -- Fall 2: anmelden nötig -------------------------------------------
        ColumnLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.abstandL
            Layout.rightMargin: Theme.abstandL
            spacing: Theme.abstandS
            visible: dlg.pruefung.ok && !publizieren.angemeldet && !publizieren.ergebnis

            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: publizieren.nutzercode
                      ? "Öffne die Seite unten und gib diesen Code ein:"
                      : "Zum Veröffentlichen brauchst du ein GitHub-Konto. "
                        + "Dein Lernset erscheint dann unter deinem Namen."
                color: Theme.textSecondary
                font.pixelSize: Theme.schriftS
            }

            // Der Gerätecode. Gross genug zum Abtippen.
            Rectangle {
                Layout.fillWidth: true
                visible: publizieren.nutzercode !== ""
                height: 92
                radius: Theme.radiusMittel
                color: Theme.surfaceElevated
                border.width: 1
                border.color: Theme.primary

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 4
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: publizieren.nutzercode
                        color: Theme.textPrimary
                        font.pixelSize: Theme.schriftXl
                        font.bold: true
                        font.letterSpacing: 3
                    }
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: publizieren.adresse
                        color: Theme.primary
                        font.pixelSize: Theme.schriftS
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: Qt.openUrlExternally(publizieren.adresse)
                        }
                    }
                }
            }
        }

        // -- Fall 3: bereit zum Einreichen ------------------------------------
        Text {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.abstandL
            Layout.rightMargin: Theme.abstandL
            visible: dlg.pruefung.ok && publizieren.angemeldet && !publizieren.ergebnis
            wrapMode: Text.WordWrap
            text: "Dein Lernset wird als Vorschlag eingereicht. Sichtbar wird es "
                  + "für alle erst, wenn Lars es freigegeben hat. Deinen "
                  + "Fortschritt enthält es nicht."
            color: Theme.textSecondary
            font.pixelSize: Theme.schriftS
        }

        // -- Fall 4: eingereicht ----------------------------------------------
        ColumnLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.abstandL
            Layout.rightMargin: Theme.abstandL
            spacing: Theme.abstandXs
            visible: publizieren.ergebnis !== ""

            Text {
                text: "Eingereicht — jetzt wartet es auf Freigabe."
                color: Theme.success
                font.pixelSize: Theme.schriftM
            }
            Text {
                Layout.fillWidth: true
                text: publizieren.ergebnis
                color: Theme.primary
                font.pixelSize: Theme.schriftS
                elide: Text.ElideMiddle
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: Qt.openUrlExternally(publizieren.ergebnis)
                }
            }
        }
    }

    footer: RowLayout {
        Layout.fillWidth: true
        spacing: Theme.abstandXs

        PrimaryButton {
            Layout.leftMargin: Theme.abstandL
            Layout.bottomMargin: Theme.abstandM
            implicitHeight: 32
            Layout.preferredWidth: 110
            sekundaer: true
            visible: publizieren.angemeldet && !publizieren.ergebnis
            text: "Abmelden"
            onClicked: publizieren.abmelden()
        }

        Item { Layout.fillWidth: true }

        PrimaryButton {
            Layout.bottomMargin: Theme.abstandM
            implicitHeight: 34
            Layout.preferredWidth: 120
            sekundaer: true
            text: publizieren.ergebnis ? "Fertig" : "Abbrechen"
            onClicked: dlg.close()
        }

        PrimaryButton {
            Layout.rightMargin: Theme.abstandL
            Layout.bottomMargin: Theme.abstandM
            implicitHeight: 34
            // Breit genug fuer die laengste Beschriftung, sonst steht dort
            // "Mit GitHub anmel…".
            Layout.preferredWidth: 186
            visible: dlg.pruefung.ok && !publizieren.ergebnis
            enabled: !publizieren.laeuft
            text: publizieren.laeuft
                  ? "…"
                  : publizieren.angemeldet ? "Einreichen" : "Mit GitHub anmelden"
            onClicked: publizieren.angemeldet
                       ? publizieren.reicheEin(dlg.lernsetId)
                       : publizieren.anmelden()
        }
    }
}
