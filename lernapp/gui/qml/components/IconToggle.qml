// Kleiner Schalter mit Symbol fuer die Kopfzeile der Seitenleiste.
import QtQuick
import QtQuick.Controls.Basic
import theme

ToolButton {
    id: schalter
    property string symbol: ""
    property bool aktiv: true
    property string hinweis: ""

    implicitWidth: 34
    implicitHeight: 34
    hoverEnabled: true
    ToolTip.visible: hovered && hinweis !== ""
    ToolTip.text: hinweis
    ToolTip.delay: 400

    background: Rectangle {
        radius: Theme.radiusKlein
        color: !schalter.enabled ? "transparent"
             : schalter.down ? Theme.border
             : schalter.hovered ? Theme.surfaceElevated : "transparent"
        border.width: schalter.activeFocus ? 1 : 0
        border.color: Theme.primary
        Behavior on color { ColorAnimation { duration: Theme.dauerSchnell } }
    }
    contentItem: Text {
        text: schalter.symbol
        font.pixelSize: 16
        color: !schalter.enabled ? Theme.textDisabled
             : schalter.aktiv ? Theme.textSecondary : Theme.textDisabled
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        opacity: schalter.aktiv ? 1.0 : 0.55
        Behavior on opacity { NumberAnimation { duration: Theme.dauerSchnell } }
        Behavior on color { ColorAnimation { duration: Theme.dauerSchnell } }
    }
}
