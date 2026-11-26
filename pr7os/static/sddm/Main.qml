// Paragon PR7-OS login screen (SDDM, Qt 6). Plain QtQuick only: SDDM gives the theme `sddm` (login, power),
// `userModel`, `sessionModel`, `keyboard` and `config`; tests render this file with stand-ins for them.
import QtQuick 2.15

Rectangle {
    id: root
    width: 1920
    height: 1080
    color: "#060407"

    readonly property string family: "Inter"
    property int userIndex: userModel.lastIndex >= 0 ? userModel.lastIndex : 0
    property int sessionIndex: sessionModel.lastIndex >= 0 ? sessionModel.lastIndex : 0
    property string error: ""

    function login() {
        root.error = ""
        sddm.login(users.currentItem ? users.currentItem.login : "", password.text, root.sessionIndex)
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            root.error = "WRONG PASSWORD, TRY AGAIN"
            password.text = ""
            password.forceActiveFocus()
        }
    }

    // The models' current entries: a ListView gives the roles of its current row. It must be visible and have a
    // size (a hidden or empty one creates no rows, so currentItem would stay null); opacity 0 keeps it unseen.
    ListView {
        id: users
        width: 1; height: 1; opacity: 0; interactive: false
        model: userModel
        currentIndex: root.userIndex
        delegate: Item {
            width: 1; height: 1
            property string login: model.name
            property string shown: model.realName && model.realName.length ? model.realName : model.name
            property string picture: model.icon ? model.icon : ""
        }
    }
    ListView {
        id: sessions
        width: 1; height: 1; opacity: 0; interactive: false
        model: sessionModel
        currentIndex: root.sessionIndex
        delegate: Item { width: 1; height: 1; property string shown: model.name }
    }

    Image {
        anchors.fill: parent
        source: config.background ? config.background : "background.png"
        fillMode: Image.PreserveAspectCrop
    }
    Rectangle { anchors.fill: parent; color: "#73060407" }

    // PARAGON and the PR7-OS mark, top left
    Row {
        x: 48; y: 40
        spacing: 14
        Text {
            text: "PARAGON"; color: "#E8E8EA"; font.family: root.family; font.pixelSize: 22
            anchors.verticalCenter: parent.verticalCenter
        }
        Image { source: "mark.png"; height: 40; fillMode: Image.PreserveAspectFit; smooth: true }
    }

    // the clock
    Text {
        id: clock
        anchors.horizontalCenter: parent.horizontalCenter
        y: 170
        color: "#E8E8EA"; font.family: root.family; font.pixelSize: 112
        text: Qt.formatTime(new Date(), "hh:mm")
    }
    Text {
        id: date
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: clock.bottom
        color: "#B9B5B8"; font.family: root.family; font.pixelSize: 15; font.weight: Font.DemiBold
        font.letterSpacing: 2.5
        text: Qt.formatDate(new Date(), "dddd d MMMM").toUpperCase()
    }
    Timer {
        interval: 1000; running: true; repeat: true
        onTriggered: {
            clock.text = Qt.formatTime(new Date(), "hh:mm")
            date.text = Qt.formatDate(new Date(), "dddd d MMMM").toUpperCase()
        }
    }

    // the account: a ring in the family gradient around the picture (or the first letter)
    Rectangle {
        id: ring
        anchors.horizontalCenter: parent.horizontalCenter
        y: 400
        width: 124; height: 124; radius: 62
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "#FF0743" }
            GradientStop { position: 0.5; color: "#FA3632" }
            GradientStop { position: 1.0; color: "#F2781E" }
        }
        Rectangle {
            anchors.centerIn: parent
            width: 116; height: 116; radius: 58
            color: "#1C1C20"
            clip: true
            Text {
                anchors.centerIn: parent
                visible: picture.status !== Image.Ready
                text: users.currentItem ? users.currentItem.shown.charAt(0).toUpperCase() : ""
                color: "#E8E8EA"; font.family: root.family; font.pixelSize: 46; font.weight: Font.DemiBold
            }
            Image {
                id: picture
                anchors.fill: parent
                source: users.currentItem && users.currentItem.picture.length ? users.currentItem.picture : ""
                fillMode: Image.PreserveAspectCrop
                visible: status === Image.Ready
            }
        }
        MouseArea {   // several accounts: a click goes to the next one
            anchors.fill: parent
            enabled: users.count > 1
            onClicked: root.userIndex = (root.userIndex + 1) % users.count
        }
    }
    Text {
        id: name
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: ring.bottom; anchors.topMargin: 16
        text: users.currentItem ? users.currentItem.shown : ""
        color: "#E8E8EA"; font.family: root.family; font.pixelSize: 22; font.weight: Font.DemiBold
    }

    // the password
    Rectangle {
        id: field
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: name.bottom; anchors.topMargin: 28
        width: 380; height: 48; radius: 12
        color: "#E60C0A0D"
        border.color: "#3A3238"; border.width: 1
        TextInput {
            id: password
            anchors.left: parent.left; anchors.leftMargin: 18
            anchors.right: go.left; anchors.rightMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            echoMode: TextInput.Password
            passwordCharacter: "•"
            color: "#E8E8EA"; font.family: root.family; font.pixelSize: 16
            selectionColor: "#E8303A"
            focus: true
            clip: true
            Keys.onReturnPressed: root.login()
            Keys.onEnterPressed: root.login()
        }
        Text {
            anchors.left: password.left; anchors.verticalCenter: parent.verticalCenter
            visible: password.text.length === 0
            text: "PASSWORD"; color: "#6E6A70"; font.family: root.family; font.pixelSize: 13
            font.weight: Font.DemiBold; font.letterSpacing: 1.5
        }
        Rectangle {      // the family gradient under the field
            anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width - 24; height: 2
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#FF0743" }
                GradientStop { position: 0.5; color: "#FA3632" }
                GradientStop { position: 1.0; color: "#F2781E" }
            }
        }
        Rectangle {
            id: go
            anchors.right: parent.right; anchors.rightMargin: 6
            anchors.verticalCenter: parent.verticalCenter
            width: 36; height: 36; radius: 9
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#FF0743" }
                GradientStop { position: 1.0; color: "#F2781E" }
            }
            Text {
                anchors.centerIn: parent
                text: "→"; color: "#FFFFFF"; font.family: root.family; font.pixelSize: 20
                font.weight: Font.DemiBold
            }
            MouseArea { anchors.fill: parent; onClicked: root.login() }
        }
    }
    Text {
        id: status
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: field.bottom; anchors.topMargin: 14
        color: root.error.length ? "#FF3B2F" : "#8A8A92"
        font.family: root.family; font.pixelSize: 12; font.weight: Font.DemiBold; font.letterSpacing: 1.5
        text: {
            if (root.error.length) return root.error
            var caps = (typeof keyboard !== "undefined" && keyboard && keyboard.capsLock) ? "CAPS LOCK IS ON"
                                                                                        : "CAPS LOCK IS OFF"
            var layout = ""
            if (typeof keyboard !== "undefined" && keyboard && keyboard.layouts && keyboard.layouts.length)
                layout = "  ·  " + keyboard.layouts[keyboard.currentLayout].shortName.toUpperCase()
            return caps + layout
        }
    }

    // the session (a click goes to the next one)
    Row {
        x: 48
        anchors.bottom: parent.bottom; anchors.bottomMargin: 48
        spacing: 14
        Text {
            text: "SESSION"; color: "#8A8A92"; font.family: root.family; font.pixelSize: 12
            font.weight: Font.DemiBold; font.letterSpacing: 1.5
        }
        Text {
            text: sessions.currentItem ? sessions.currentItem.shown.toUpperCase() : ""
            color: "#E8E8EA"; font.family: root.family; font.pixelSize: 12
            font.weight: Font.DemiBold; font.letterSpacing: 1.5
            MouseArea {
                anchors.fill: parent
                onClicked: root.sessionIndex = (root.sessionIndex + 1) % Math.max(1, sessions.count)
            }
        }
    }

    // sleep, restart, shut down
    Row {
        anchors.right: parent.right; anchors.rightMargin: 48
        anchors.bottom: parent.bottom; anchors.bottomMargin: 36
        spacing: 12
        Repeater {
            model: [
                { label: "SLEEP", can: sddm.canSuspend, act: function () { sddm.suspend() } },
                { label: "RESTART", can: sddm.canReboot, act: function () { sddm.reboot() } },
                { label: "SHUT DOWN", can: sddm.canPowerOff, act: function () { sddm.powerOff() } }
            ]
            delegate: Rectangle {
                visible: modelData.can
                width: 150; height: 44; radius: 10
                color: hover.containsMouse ? "#1C1C20" : "#D90C0A0D"
                border.color: "#3A3238"; border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: modelData.label; color: "#E8E8EA"; font.family: root.family; font.pixelSize: 12
                    font.weight: Font.DemiBold; font.letterSpacing: 1.2
                }
                MouseArea { id: hover; anchors.fill: parent; hoverEnabled: true; onClicked: modelData.act() }
            }
        }
    }

    Component.onCompleted: password.forceActiveFocus()
}
