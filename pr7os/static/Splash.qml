// Paragon PR7-OS: the splash between login and the desktop (KSplash). Plasma sets `stage` 1..6 as it starts.
import QtQuick 2.15

Rectangle {
    id: root
    color: "#060407"
    property int stage

    Image {
        id: mark
        source: "images/mark.png"
        anchors.centerIn: parent
        anchors.verticalCenterOffset: -30
        width: 520
        height: 100
        fillMode: Image.PreserveAspectFit
        smooth: true
    }

    Rectangle {           // the track
        id: track
        anchors.top: mark.bottom
        anchors.topMargin: 40
        anchors.horizontalCenter: parent.horizontalCenter
        width: 320
        height: 4
        radius: 2
        color: "#1C1C20"

        Rectangle {       // the family gradient, growing with Plasma's start-up stages
            height: parent.height
            radius: 2
            width: parent.width * Math.min(1, root.stage / 6)
            Behavior on width { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#FF0743" }
                GradientStop { position: 0.5; color: "#FA3632" }
                GradientStop { position: 1.0; color: "#F2781E" }
            }
        }
    }
}
