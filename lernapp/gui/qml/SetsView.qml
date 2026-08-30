// Seitenleiste: Ordner und Lernsets.
// Drag & Drop ist eine Bequemlichkeit - jede Aktion ist auch über das
// Kontextmenü erreichbar.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts
import theme
import "components"

Rectangle {
    id: leiste
    color: Theme.surface

    signal bearbeiten(string lernsetId)
    signal neuAnlegen(string ordner)
    signal marktplatzOeffnen()
    signal veroeffentlichen(string lernsetId)

    property string ziehtId: ""
    property string zielOrdner: ""

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.abstandS
        spacing: Theme.abstandS

        RowLayout {
            Layout.fillWidth: true
            Text {
                Layout.fillWidth: true
                text: "Lernsets"
                color: Theme.textPrimary
                font.pixelSize: Theme.schriftL
                font.bold: true
                leftPadding: Theme.abstandXs
            }
            IconToggle {
                symbol: einstellungen.sound ? "🔊" : "🔇"
                aktiv: einstellungen.sound
                enabled: einstellungen.tonVerfuegbar
                hinweis: !einstellungen.tonVerfuegbar
                         ? "Auf diesem System ist kein Ton verfügbar"
                         : (einstellungen.sound ? "Ton aus" : "Ton an")
                           + "  (" + einstellungen.kuerzel.tonUmschalten + ")"
                onClicked: einstellungen.soundUmschalten()
            }
            IconToggle {
                symbol: einstellungen.dark ? "☀" : "☾"
                hinweis: (einstellungen.dark ? "Helles Design" : "Dunkles Design")
                         + "  (" + einstellungen.kuerzel.themeUmschalten + ")"
                onClicked: einstellungen.themeUmschalten()
            }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            ColumnLayout {
                width: leiste.width - 2 * Theme.abstandS
                spacing: Theme.abstandXs

                Repeater {
                    model: sets.ordner
                    delegate: Rectangle {
                        id: ordnerBlock
                        required property var modelData
                        readonly property string ordnerName: modelData.name
                        readonly property bool zu: sets.eingeklappt.indexOf(modelData.name) >= 0

                        Layout.fillWidth: true
                        implicitHeight: ordnerSpalte.implicitHeight + 2 * Theme.abstandXs
                        radius: Theme.radiusMittel
                        color: leiste.zielOrdner === ordnerName && leiste.ziehtId !== ""
                               ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.18)
                               : Theme.surfaceElevated
                        border.width: 1
                        border.color: leiste.zielOrdner === ordnerName && leiste.ziehtId !== ""
                                      ? Theme.primary : "transparent"
                        Behavior on color { ColorAnimation { duration: Theme.dauerSchnell } }

                        DropArea {
                            anchors.fill: parent
                            onEntered: leiste.zielOrdner = ordnerBlock.ordnerName
                            onExited: if (leiste.zielOrdner === ordnerBlock.ordnerName) leiste.zielOrdner = ""
                            onDropped: function(drop) {
                                if (leiste.ziehtId !== "")
                                    sets.lernsetVerschieben(leiste.ziehtId, ordnerBlock.ordnerName)
                                leiste.zielOrdner = ""
                                leiste.ziehtId = ""
                            }
                        }

                        ColumnLayout {
                            id: ordnerSpalte
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: Theme.abstandXs
                            spacing: 3

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                // Der Pfeil dreht sich beim Umklappen, damit
                                // sichtbar ist, was gerade passiert ist.
                                Text {
                                    text: "▸"
                                    color: Theme.textSecondary
                                    font.pixelSize: 13
                                    leftPadding: Theme.abstandXs
                                    rotation: ordnerBlock.zu ? 0 : 90
                                    Behavior on rotation {
                                        NumberAnimation { duration: Theme.dauerSchnell }
                                    }
                                    // Die Klickflaeche gehoert IN den Text, nicht
                                    // daneben: ein MouseArea direkt im RowLayout
                                    // wird selbst zum Layout-Element und draengt
                                    // die Beschriftungen hinaus.
                                    MouseArea {
                                        anchors.fill: parent
                                        anchors.margins: -4
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: sets.klappeUm(ordnerBlock.ordnerName)
                                    }
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: ordnerBlock.ordnerName
                                          + (ordnerBlock.zu
                                             ? "   " + ordnerBlock.modelData.lernsets.length
                                             : "")
                                    color: Theme.textPrimary
                                    font.pixelSize: Theme.schriftM
                                    font.bold: true
                                    elide: Text.ElideRight
                                    leftPadding: Theme.abstandXs

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: sets.klappeUm(ordnerBlock.ordnerName)
                                    }
                                }
                                ToolButton {
                                    implicitWidth: 28; implicitHeight: 26
                                    onClicked: leiste.neuAnlegen(ordnerBlock.ordnerName)
                                    ToolTip.visible: hovered
                                    ToolTip.text: "Neues Lernset in „" + ordnerBlock.ordnerName + "“"
                                    background: Rectangle {
                                        radius: Theme.radiusKlein
                                        color: parent.hovered ? Theme.primary : "transparent"
                                    }
                                    contentItem: Text {
                                        text: "+"
                                        color: parent.hovered ? Theme.onPrimary : Theme.textSecondary
                                        font.pixelSize: 17; font.bold: true
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                            }

                            Repeater {
                                // Beim Zuklappen wird der Inhalt gar nicht
                                // erst gebaut - das haelt lange Listen
                                // fluessig.
                                model: ordnerBlock.zu ? [] : ordnerBlock.modelData.lernsets
                                delegate: Item {
                                    id: eintrag
                                    required property var modelData
                                    Layout.fillWidth: true
                                    implicitHeight: 44

                                    Rectangle {
                                        id: flaeche
                                        anchors.fill: parent
                                        radius: Theme.radiusKlein
                                        color: eintrag.modelData.aktiv ? Theme.primary
                                             : zeiger.containsMouse ? Theme.border : "transparent"
                                        Behavior on color { ColorAnimation { duration: Theme.dauerSchnell } }
                                        opacity: leiste.ziehtId === eintrag.modelData.id ? 0.4 : 1.0

                                        ColumnLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: Theme.abstandS
                                            anchors.rightMargin: Theme.abstandS
                                            anchors.topMargin: 5
                                            spacing: 3
                                            Text {
                                                Layout.fillWidth: true
                                                text: eintrag.modelData.name
                                                color: eintrag.modelData.aktiv ? Theme.onPrimary : Theme.textPrimary
                                                font.pixelSize: Theme.schriftS
                                                elide: Text.ElideRight
                                            }
                                            RowLayout {
                                                Layout.fillWidth: true
                                                spacing: Theme.abstandXs
                                                ProgressTrack {
                                                    Layout.fillWidth: true
                                                    dicke: 4
                                                    anteil: eintrag.modelData.prozent / 100
                                                    fuellFarbe: eintrag.modelData.aktiv ? Theme.onPrimary : Theme.success
                                                }
                                                Text {
                                                    text: eintrag.modelData.prozent + "%"
                                                    color: eintrag.modelData.aktiv ? Theme.onPrimary : Theme.textSecondary
                                                    font.pixelSize: Theme.schriftXs
                                                }
                                            }
                                        }
                                    }

                                    MouseArea {
                                        id: zeiger
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                                        drag.target: ziehBild
                                        drag.threshold: 8

                                        onPressed: function(maus) {
                                            if (maus.button === Qt.RightButton) {
                                                kontext.lernsetId = eintrag.modelData.id
                                                kontext.lernsetName = eintrag.modelData.name
                                                kontext.quellOrdner = ordnerBlock.ordnerName
                                                kontext.popup()
                                            }
                                        }
                                        onClicked: function(maus) {
                                            if (maus.button === Qt.LeftButton && leiste.ziehtId === "")
                                                sets.waehle(eintrag.modelData.id)
                                        }
                                        onDoubleClicked: leiste.bearbeiten(eintrag.modelData.id)

                                        Item {
                                            id: ziehBild
                                            width: 1; height: 1
                                            Drag.active: zeiger.drag.active
                                            Drag.hotSpot: Qt.point(0, 0)
                                            onXChanged: if (Drag.active) leiste.ziehtId = eintrag.modelData.id
                                        }
                                        onReleased: {
                                            if (leiste.ziehtId !== "" && leiste.zielOrdner !== ""
                                                && leiste.zielOrdner !== ordnerBlock.ordnerName) {
                                                sets.lernsetVerschieben(leiste.ziehtId, leiste.zielOrdner)
                                            }
                                            leiste.ziehtId = ""
                                            leiste.zielOrdner = ""
                                        }
                                    }
                                }
                            }

                            Text {
                                visible: ordnerBlock.modelData.lernsets.length === 0
                                Layout.fillWidth: true
                                text: "leer"
                                color: Theme.textDisabled
                                font.pixelSize: Theme.schriftXs
                                leftPadding: Theme.abstandS
                                bottomPadding: Theme.abstandXs
                            }
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.abstandXs
            PrimaryButton {
                Layout.fillWidth: true
                implicitWidth: 0
                implicitHeight: 36
                sekundaer: true
                text: "+ Ordner"
                onClicked: ordnerDialog.open()
            }
            PrimaryButton {
                Layout.fillWidth: true
                implicitWidth: 0
                implicitHeight: 36
                sekundaer: true
                text: "Import"
                onClicked: importDialog.open()
            }
        }

        PrimaryButton {
            Layout.fillWidth: true
            implicitHeight: 36
            text: "Marktplatz"
            onClicked: leiste.marktplatzOeffnen()
        }
    }

    // -- Kontextmenü ---------------------------------------------------------
    Menu {
        id: kontext
        property string lernsetId: ""
        property string lernsetName: ""
        property string quellOrdner: ""

        MenuItem {
            text: "Bearbeiten"
            onTriggered: leiste.bearbeiten(kontext.lernsetId)
        }
        MenuItem {
            text: "Veröffentlichen …"
            onTriggered: leiste.veroeffentlichen(kontext.lernsetId)
        }
        MenuItem {
            text: "Exportieren …"
            onTriggered: {
                exportDialog.lernsetId = kontext.lernsetId
                exportDialog.selectedFile = exportDialog.currentFolder
                                            + "/" + sets.standardDateiname(kontext.lernsetId)
                exportDialog.open()
            }
        }
        Menu {
            title: "Verschieben nach"
            enabled: sets.ordnerNamen.length > 1
            Repeater {
                model: sets.ordnerNamen
                delegate: MenuItem {
                    required property string modelData
                    text: modelData
                    enabled: modelData !== kontext.quellOrdner
                    onTriggered: sets.lernsetVerschieben(kontext.lernsetId, modelData)
                }
            }
        }
        MenuSeparator {}
        MenuItem {
            text: "Löschen"
            onTriggered: {
                loeschDialog.lernsetId = kontext.lernsetId
                loeschDialog.lernsetName = kontext.lernsetName
                loeschDialog.open()
            }
        }
    }

    // -- Dialoge --------------------------------------------------------------
    FileDialog {
        id: exportDialog
        property string lernsetId: ""
        title: "Lernset exportieren"
        fileMode: FileDialog.SaveFile
        nameFilters: ["LernApp-Lernset (*.lernset.json)", "Alle Dateien (*)"]
        defaultSuffix: "json"
        onAccepted: sets.exportiereLernset(exportDialog.lernsetId, selectedFile.toString())
    }

    FileDialog {
        id: importDialog
        title: "Lernset importieren"
        fileMode: FileDialog.OpenFile
        nameFilters: ["LernApp-Lernset (*.lernset.json)", "JSON (*.json)", "Alle Dateien (*)"]
        onAccepted: {
            var ordner = sets.ordnerNamen.length > 0 ? sets.ordnerNamen[0] : ""
            var id = sets.importiereLernset(selectedFile.toString(), ordner)
            if (id !== "") sets.waehle(id)
        }
    }

    Dialog {
        id: ordnerDialog
        anchors.centerIn: Overlay.overlay
        modal: true
        title: "Neuer Ordner"
        standardButtons: Dialog.Ok | Dialog.Cancel
        onOpened: ordnerFeld.forceActiveFocus()
        onAccepted: { sets.ordnerAnlegen(ordnerFeld.text); ordnerFeld.text = "" }
        background: Rectangle {
            color: Theme.surface; radius: Theme.radiusMittel
            border.color: Theme.border; border.width: 1
        }
        contentItem: AnswerField {
            id: ordnerFeld
            implicitWidth: 300
            placeholderText: "Ordnername"
            onAccepted: ordnerDialog.accept()
        }
    }

    Dialog {
        id: loeschDialog
        property string lernsetId: ""
        property string lernsetName: ""
        anchors.centerIn: Overlay.overlay
        modal: true
        title: "Lernset löschen?"
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: sets.lernsetLoeschen(loeschDialog.lernsetId)
        background: Rectangle {
            color: Theme.surface; radius: Theme.radiusMittel
            border.color: Theme.border; border.width: 1
        }
        contentItem: Text {
            text: "„" + loeschDialog.lernsetName + "“ wird entfernt.\n"
                  + "Der gespeicherte Fortschritt bleibt erhalten."
            color: Theme.textPrimary
            font.pixelSize: Theme.schriftM
            wrapMode: Text.WordWrap
        }
    }
}
