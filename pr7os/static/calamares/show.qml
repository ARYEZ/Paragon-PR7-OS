// Paragon PR7-OS installer slideshow (Calamares slideshow API 2): what's coming, while the files are copied.
import QtQuick 2.15

Rectangle {
    id: show
    color: "#060407"
    property int slide: 0
    property var slides: [
        ["THE PARAGON FAMILY", "Files, text, media, images, PDF, archives, passwords, backups and more:\nthe Paragon apps are already in the menu."],
        ["OBSIDIAN OR AURORA", "Two finishes, one choice for the whole system:\nSystem Settings, Global Theme."],
        ["BASED ON DEBIAN 13", "Debian's security updates and its thousands of packages,\nin the Paragon look."]
    ]
    function onActivate() { timer.running = true }
    function onLeave() { timer.running = false }

    Timer { id: timer; interval: 9000; repeat: true; onTriggered: show.slide = (show.slide + 1) % show.slides.length }

    Image {
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height * 0.18
        source: "welcome.png"
        width: Math.min(parent.width * 0.6, 520)
        fillMode: Image.PreserveAspectFit
        smooth: true
    }
    Text {
        id: heading
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height * 0.55
        text: show.slides[show.slide][0]
        color: "#E8E8EA"; font.family: "Bebas Neue"; font.pixelSize: 26; font.letterSpacing: 2
    }
    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: heading.bottom; anchors.topMargin: 12
        width: 120; height: 3; radius: 1.5
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "#FF0743" }
            GradientStop { position: 0.5; color: "#FA3632" }
            GradientStop { position: 1.0; color: "#F2781E" }
        }
    }
    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: heading.bottom; anchors.topMargin: 32
        horizontalAlignment: Text.AlignHCenter
        text: show.slides[show.slide][1]
        color: "#B9B5B8"; font.family: "Bebas Neue"; font.pixelSize: 19; lineHeight: 1.3
    }
}
