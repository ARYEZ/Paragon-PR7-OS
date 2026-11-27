// Paragon PR7-OS: the lock screen's clock, as on the login screen: the time large, the date in capitals.
// Put beside Plasma's lock screen by lockscreen.py (LockScreenUi.qml's `Clock {` becomes `ParagonClock {`, every
// property it sets stays the same).
import QtQuick 2.15
import QtQuick.Layouts 1.15
import org.kde.plasma.plasma5support 2.0 as P5Support

ColumnLayout {
    spacing: 4

    Text {
        text: Qt.formatTime(timeSource.data["Local"]["DateTime"], Qt.locale(), Locale.ShortFormat)
        color: "#E8E8EA"; font.family: "Inter"; font.pixelSize: 112
        Layout.alignment: Qt.AlignHCenter
    }
    Text {
        text: Qt.formatDate(timeSource.data["Local"]["DateTime"], "dddd d MMMM").toUpperCase()
        color: "#B9B5B8"; font.family: "Inter"; font.pixelSize: 15; font.weight: Font.DemiBold
        font.letterSpacing: 2.5
        Layout.alignment: Qt.AlignHCenter
    }
    P5Support.DataSource {
        id: timeSource
        engine: "time"
        connectedSources: ["Local"]
        interval: 1000
    }
}
