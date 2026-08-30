// Marktplatz: fertige Lernsets direkt aus dem Netz übernehmen.
//
// Stellt nur dar. Laden, Prüfsumme und Ablage macht das ViewModel; hier
// steht keine Schwelle und keine Regel.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import theme
import "components"

Dialog {
    id: dlg
    modal: true
    title: "Marktplatz"
    width: 620
    height: 620
    closePolicy: Popup.CloseOnEscape

    // Leerer Filter heisst: alle Fächer.
    property string fach: ""

    function oeffnen() {
        fach = ""
        open()
        marktplatz.einmalLaden()
    }

    background: Rectangle {
        color: Theme.surface
        radius: Theme.radiusGross
        border.width: 1
        border.color: Theme.border
    }

    header: ColumnLayout {
        spacing: Theme.abstandXs

        RowLayout {
            Layout.fillWidth: true
            Layout.margins: Theme.abstandL
            Layout.bottomMargin: 0
            spacing: Theme.abstandS

            ColumnLayout {
                spacing: 2
                Text {
                    text: "Marktplatz"
                    color: Theme.textPrimary
                    font.pixelSize: Theme.schriftL
                    font.bold: true
                }
                Text {
                    text: marktplatz.laedt
                          ? "wird geladen …"
                          : marktplatz.eintraege.length > 0
                            ? marktplatz.eintraege.length + " Lernsets · Stand "
                              + marktplatz.aktualisiertAm
                            : "keine Verbindung"
                    color: Theme.textSecondary
                    font.pixelSize: Theme.schriftS
                }
            }

            Item { Layout.fillWidth: true }

            PrimaryButton {
                sekundaer: true
                implicitHeight: 32
                text: "Neu laden"
                enabled: !marktplatz.laedt
                onClicked: marktplatz.aktualisieren()
            }
        }

        // Fachfilter. Erscheint erst, wenn es etwas zu filtern gibt.
        Flow {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.abstandL
            Layout.rightMargin: Theme.abstandL
            spacing: Theme.abstandXs
            visible: marktplatz.faecher.length > 1

            Repeater {
                model: [""].concat(marktplatz.faecher)
                delegate: Rectangle {
                    required property string modelData
                    readonly property bool gewaehlt: dlg.fach === modelData

                    height: 28
                    width: beschriftung.implicitWidth + 2 * Theme.abstandS
                    radius: Theme.radiusRund
                    color: gewaehlt ? Theme.primary : "transparent"
                    border.width: 1
                    border.color: gewaehlt ? Theme.primary : Theme.border

                    Text {
                        id: beschriftung
                        anchors.centerIn: parent
                        text: modelData === "" ? "Alle" : modelData
                        color: parent.gewaehlt ? Theme.onPrimary : Theme.textSecondary
                        font.pixelSize: Theme.schriftS
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: dlg.fach = modelData
                    }
                }
            }
        }
    }

    contentItem: Item {
        ListView {
            id: liste
            anchors.fill: parent
            anchors.margins: Theme.abstandS
            clip: true
            spacing: Theme.abstandXs
            model: marktplatz.eintraege

            ScrollBar.vertical: ScrollBar {}

            delegate: Rectangle {
                required property var modelData
                readonly property bool sichtbar: dlg.fach === "" || modelData.fach === dlg.fach

                width: liste.width - (liste.ScrollBar.vertical.visible ? 12 : 0)
                height: sichtbar ? 60 : 0
                visible: sichtbar
                radius: Theme.radiusMittel
                color: zeigerBereich.containsMouse ? Theme.surfaceElevated : "transparent"
                border.width: 1
                border.color: Theme.border

                MouseArea {
                    id: zeigerBereich
                    anchors.fill: parent
                    hoverEnabled: true
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.abstandM
                    anchors.rightMargin: Theme.abstandS
                    spacing: Theme.abstandS

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            Layout.fillWidth: true
                            text: modelData.name
                            color: Theme.textPrimary
                            font.pixelSize: Theme.schriftM
                            elide: Text.ElideRight
                        }
                        Text {
                            text: modelData.fach + " · " + modelData.karten + " Karten"
                            color: Theme.textSecondary
                            font.pixelSize: Theme.schriftS
                        }
                    }

                    Text {
                        text: "schon da"
                        visible: modelData.vorhanden
                        color: Theme.textDisabled
                        font.pixelSize: Theme.schriftXs
                    }

                    PrimaryButton {
                        implicitHeight: 32
                        implicitWidth: 108
                        sekundaer: modelData.vorhanden
                        text: modelData.vorhanden ? "Nochmal" : "Übernehmen"
                        enabled: !marktplatz.laedt
                        onClicked: marktplatz.uebernehmen(modelData.id)
                    }
                }
            }
        }

        // Leerer Zustand. Ohne den steht der Nutzer vor einer weissen Fläche
        // und weiss nicht, ob es lädt oder kaputt ist.
        ColumnLayout {
            anchors.centerIn: parent
            width: parent.width - 2 * Theme.abstandXl
            spacing: Theme.abstandS
            visible: marktplatz.eintraege.length === 0

            Text {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: marktplatz.laedt ? "Lernsets werden geladen …"
                                       : "Keine Lernsets erreichbar."
                color: Theme.textSecondary
                font.pixelSize: Theme.schriftM
            }
            Text {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                visible: !marktplatz.laedt
                text: "Der Marktplatz braucht eine Internetverbindung. "
                      + "Eigene Lernsets kannst du jederzeit über Import einlesen."
                color: Theme.textDisabled
                font.pixelSize: Theme.schriftS
            }
        }
    }

    footer: RowLayout {
        Layout.fillWidth: true

        Text {
            Layout.leftMargin: Theme.abstandL
            Layout.bottomMargin: Theme.abstandM
            text: "Übernommene Lernsets starten ohne Punkte bei null."
            color: Theme.textDisabled
            font.pixelSize: Theme.schriftXs
        }
        Item { Layout.fillWidth: true }
        PrimaryButton {
            Layout.rightMargin: Theme.abstandL
            Layout.bottomMargin: Theme.abstandM
            implicitHeight: 34
            text: "Schließen"
            onClicked: dlg.close()
        }
    }
}
