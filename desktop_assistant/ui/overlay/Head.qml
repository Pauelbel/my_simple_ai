import QtQuick
import QtQuick.Controls
import QtQuick.Window
import QtMultimedia
import "../components" as Ui

Window {
    id: overlay
    width: 136; height: 136; visible: true; color: "transparent"
    flags: Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus | (assistant.alwaysOnTop ? Qt.WindowStaysOnTopHint : 0)
    title: "Desktop Assistant"

    property point dragStart: Qt.point(0, 0)
    property point windowStart: Qt.point(0, 0)
    property int dragButton: Qt.NoButton
    property bool dragging: false
    property bool suppressClick: false
    property string dictationStatus: dictation ? dictation.status : "idle"

    SoundEffect {
        id: recordingStartSound
        objectName: "recordingStartSound"
        source: Qt.resolvedUrl("../../assets/recording-start.wav")
        volume: 0.45
    }

    OrbAnimation {
        id: orb
        objectName: "assistantOrb"
        anchors.centerIn: parent
        width: 128; height: 128
        status: overlay.dictationStatus
    }

    MouseArea {
        id: mouseArea
        objectName: "orbMouseArea"
        anchors.fill: orb
        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
        preventStealing: true
        property bool nativeMoving: false
        cursorShape: overlay.dragging ? Qt.ClosedHandCursor : overlay.dragButton !== Qt.NoButton ? Qt.ClosedHandCursor : Qt.OpenHandCursor
        onPressed: function(mouse) {
            if (mouse.button === Qt.LeftButton || mouse.button === Qt.MiddleButton) {
                overlay.dragStart = Qt.point(mouse.x, mouse.y)
                overlay.windowStart = Qt.point(overlay.x, overlay.y)
                overlay.dragButton = mouse.button
                overlay.suppressClick = false
                overlay.dragging = false
                nativeMoving = false
            }
        }
        onPositionChanged: function(mouse) {
            if (overlay.dragButton === Qt.NoButton || !(mouse.buttons & overlay.dragButton)) return
            var dx = mouse.x - overlay.dragStart.x
            var dy = mouse.y - overlay.dragStart.y
            var distance = Math.sqrt(dx * dx + dy * dy)
            if (distance >= 6 && !overlay.dragging) {
                overlay.suppressClick = true
                nativeMoving = overlay.dragButton === Qt.LeftButton ? overlay.startSystemMove() : false
                overlay.dragging = true
            }
            if (overlay.dragging && !nativeMoving) {
                overlay.x = Math.round(overlay.windowStart.x + dx)
                overlay.y = Math.round(overlay.windowStart.y + dy)
            }
        }
        onReleased: function(mouse) {
            if (mouse.button !== overlay.dragButton) return
            var startRecording = mouse.button === Qt.LeftButton && !overlay.suppressClick && !overlay.dragging
            overlay.dragging = false
            overlay.dragButton = Qt.NoButton
            nativeMoving = false
            if (startRecording) dictation.toggleRecording()
        }
        onCanceled: { overlay.dragging = false; overlay.dragButton = Qt.NoButton; nativeMoving = false }
        onClicked: function(mouse) { if (mouse.button === Qt.RightButton) assistant.showNotes() }
    }

    Component.onCompleted: {
        Ui.Theme.dark = assistant.darkTheme
        assistant.registerOverlay(overlay)
    }

    Connections {
        target: assistant
        function onNotification(message) { assistant.showError(message) }
        function onThemeChanged() { Ui.Theme.dark = assistant.darkTheme }
    }
    Connections {
        target: dictation
        function onStatusChanged() { if (dictation.status === "recording") recordingStartSound.play() }
    }
}
