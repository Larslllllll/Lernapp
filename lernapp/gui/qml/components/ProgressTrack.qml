// Weich animierter Fortschrittsbalken.
import QtQuick
import theme

Rectangle {
    id: track
    property real anteil: 0          // 0..1
    property color fuellFarbe: Theme.primary
    property int dicke: 10

    height: dicke
    radius: dicke / 2
    color: Theme.border

    Rectangle {
        width: Math.max(0, Math.min(1, track.anteil)) * parent.width
        height: parent.height
        radius: parent.radius
        color: track.fuellFarbe
        Behavior on width { NumberAnimation { duration: Theme.dauerLangsam; easing.type: Easing.OutCubic } }
        Behavior on color { ColorAnimation { duration: Theme.dauerNormal } }
    }
}
