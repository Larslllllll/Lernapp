// Combo-Anzeige mit dezentem Puls. Die Schwellen kommen aus dem Core,
// hier wird nur eingefärbt.
import QtQuick
import theme

Rectangle {
    id: badge
    property int wert: 0

    readonly property color stufenFarbe: wert >= 7 ? Theme.comboHoch
                                       : wert >= 4 ? Theme.comboMittel
                                       : wert >= 2 ? Theme.comboNiedrig
                                       : Theme.textSecondary

    function pulsieren() { puls.restart() }

    implicitWidth: 92
    implicitHeight: 42
    radius: Theme.radiusRund
    color: Theme.surface
    border.width: 1
    border.color: wert >= 2 ? stufenFarbe : Theme.border
    Behavior on border.color { ColorAnimation { duration: Theme.dauerNormal } }

    Row {
        anchors.centerIn: parent
        spacing: Theme.abstandXs
        Text {
            text: "🔥"; font.pixelSize: 16
            anchors.verticalCenter: parent.verticalCenter
            opacity: badge.wert >= 2 ? 1.0 : 0.45
            Behavior on opacity { NumberAnimation { duration: Theme.dauerNormal } }
        }
        Text {
            text: badge.wert
            font.pixelSize: Theme.schriftL
            font.bold: true
            color: badge.stufenFarbe
            anchors.verticalCenter: parent.verticalCenter
            Behavior on color { ColorAnimation { duration: Theme.dauerNormal } }
        }
    }

    SequentialAnimation {
        id: puls
        NumberAnimation { target: badge; property: "scale"; to: 1.16; duration: 110; easing.type: Easing.OutBack }
        NumberAnimation { target: badge; property: "scale"; to: 1.0;  duration: 190; easing.type: Easing.OutCubic }
    }
}
