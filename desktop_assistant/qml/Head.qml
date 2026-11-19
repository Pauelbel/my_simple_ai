import QtQuick
import QtQuick.Controls
import QtQuick.Window
import QtMultimedia
import "notes" as Ui

Window {
    id: overlay
    width: 136; height: 136; visible: true; color: "transparent"
    flags: Qt.FramelessWindowHint | (menuFocus ? 0 : Qt.WindowDoesNotAcceptFocus) | (assistant.alwaysOnTop ? Qt.WindowStaysOnTopHint : 0)
    title: "Desktop Assistant"

    property point dragStart: Qt.point(0, 0)
    property bool menuFocus: false
    property point windowStart: Qt.point(0, 0)
    property int dragButton: Qt.NoButton
    property bool dragging: false
    property bool suppressClick: false
    property color neon: assistant.status === "recording" ? "#ff5f9d" : assistant.status === "processing" ? "#ffd35a" : "#35e8ff"
    Behavior on neon { ColorAnimation { duration: 320; easing.type: Easing.InOutQuad } }

    SoundEffect {
        id: recordingStartSound
        objectName: "recordingStartSound"
        source: Qt.resolvedUrl("../assets/recording-start.wav")
        volume: 0.45
    }

    Item {
        id: orb
        anchors.centerIn: parent
        width: 128; height: 128
        // The sphere is painted as layered glass and drifting light, independently
        // of the pointer. The window itself remains transparent.
        Canvas {
            id: sphere
            anchors.fill: parent
            property real phase: 0
            property real breath: 0
            onPhaseChanged: requestPaint()
            onBreathChanged: requestPaint()
            Connections {
                target: assistant
                function onStatusChanged() {
                    sphere.requestPaint()
                    if (assistant.status === "recording") recordingStartSound.play()
                }
            }
            NumberAnimation on phase { from: 0; to: Math.PI * 2; duration: 6500; loops: Animation.Infinite }
            SequentialAnimation on breath {
                loops: Animation.Infinite
                NumberAnimation { to: 1; duration: 1250; easing.type: Easing.InOutSine }
                NumberAnimation { to: 0; duration: 1250; easing.type: Easing.InOutSine }
            }
            onPaint: {
                var c = getContext("2d")
                c.reset()
                var x = width / 2, y = height / 2
                var r = 40
                var t = phase
                var recording = assistant.status === "recording"
                var processing = assistant.status === "processing"
                var bright = recording ? "255,72,155" : processing ? "255,181,75" : "71,202,255"
                var secondary = recording ? "164,54,255" : processing ? "255,91,113" : "165,53,255"
                var accent = recording ? "255,130,110" : processing ? "255,220,110" : "255,80,185"

                function glow(cx, cy, radius, rgb, alpha) {
                    var g = c.createRadialGradient(cx, cy, 0, cx, cy, radius)
                    g.addColorStop(0, "rgba(" + rgb + "," + alpha + ")")
                    g.addColorStop(1, "rgba(" + rgb + ",0)")
                    c.fillStyle = g
                    c.fillRect(cx - radius, cy - radius, radius * 2, radius * 2)
                }
                // A breathing corona surrounds a sphere of constant size.
                var corona = c.createRadialGradient(x, y, r - 3, x, y, r + 22)
                corona.addColorStop(0, "rgba(" + secondary + ",0)")
                corona.addColorStop(0.2, "rgba(" + bright + "," + (0.35 + breath * 0.4) + ")")
                corona.addColorStop(0.42, "rgba(" + secondary + "," + (0.24 + breath * 0.3) + ")")
                corona.addColorStop(0.7, "rgba(" + accent + "," + (0.08 + breath * 0.14) + ")")
                corona.addColorStop(1, "rgba(" + secondary + ",0)")
                c.fillStyle = corona; c.fillRect(x - 62, y - 62, 124, 124)
                // A dark glass body with layers of moving light inside it.
                c.save()
                c.beginPath(); c.arc(x, y, r, 0, Math.PI * 2); c.clip()
                var base = c.createLinearGradient(x - r, y - r, x + r, y + r)
                base.addColorStop(0, "#142b42"); base.addColorStop(0.3, "#080d20")
                base.addColorStop(0.65, "#0c0820"); base.addColorStop(1, "#271242")
                c.fillStyle = base; c.fillRect(x - r, y - r, r * 2, r * 2)
                glow(x + Math.sin(t) * 25, y + 13 + Math.cos(t) * 18, 42, secondary, 0.75 + breath * 0.2)
                glow(x + Math.cos(t) * 26, y + 12 + Math.sin(t) * 20, 40, bright, 0.65 + breath * 0.25)
                glow(x - 24 + Math.sin(t) * 13, y - 22 + Math.cos(t) * 10, 32, bright, 0.4)

                // Veils of light flow across the interior, like liquid under glass.
                var wave = Math.sin(t) * 12
                var ribbon = c.createLinearGradient(x, y - r * 0.2, x, y + r)
                ribbon.addColorStop(0, "rgba(" + bright + ",0)")
                ribbon.addColorStop(0.45, "rgba(" + secondary + ",0.36)")
                ribbon.addColorStop(0.75, "rgba(" + bright + ",0.58)")
                ribbon.addColorStop(1, "rgba(" + secondary + ",0)")
                c.beginPath(); c.moveTo(x - r, y + wave * 0.35)
                c.bezierCurveTo(x - r * 0.5, y + r * 0.64 + wave, x + r * 0.42, y + r * 0.65 - wave, x + r, y - wave * 0.35)
                c.lineTo(x + r, y + r); c.lineTo(x - r, y + r); c.closePath()
                c.fillStyle = ribbon; c.fill()
                // Small, slowly twinkling points add depth without following the pointer.
                for (var i = 0; i < 30; ++i) {
                    var sx = x + Math.sin(i * 71.7) * r * 0.78
                    var sy = y + Math.cos(i * 43.3) * r * 0.75
                    var twinkle = 0.12 + 0.35 * (0.5 + 0.5 * Math.sin(t * 2 + i * 2.1))
                    c.beginPath(); c.arc(sx, sy, i % 7 === 0 ? 0.9 : 0.45, 0, Math.PI * 2)
                    c.fillStyle = "rgba(222,237,255," + twinkle + ")"; c.fill()
                }
                // Deep translucent center preserves the spherical volume.
                var core = c.createRadialGradient(x, y - 12, 2, x, y - 12, r * 0.85)
                core.addColorStop(0, "rgba(3,5,16,0.5)"); core.addColorStop(1, "rgba(3,5,16,0)")
                c.fillStyle = core; c.fillRect(x - r, y - r, r * 2, r * 2)
                // Curved specular highlights on the glass.
                var shine = c.createLinearGradient(x, y - r, x, y - r * 0.35)
                shine.addColorStop(0, "rgba(238,250,255,0.8)")
                shine.addColorStop(1, "rgba(193,225,255,0.03)")
                c.beginPath(); c.moveTo(x - r * 0.7, y - r * 0.58)
                c.bezierCurveTo(x - r * 0.58, y - r * 1.08, x + r * 0.48, y - r * 1.08, x + r * 0.7, y - r * 0.58)
                c.bezierCurveTo(x + r * 0.3, y - r * 0.74, x - r * 0.35, y - r * 0.74, x - r * 0.7, y - r * 0.58); c.closePath()
                c.fillStyle = shine; c.fill()
                c.restore()
            }
        }

        Item {
            id: processingIndicator
            objectName: "processingIndicator"
            anchors.centerIn: parent
            width: 42; height: 18
            visible: assistant.status === "processing"
            property real phase: 0
            NumberAnimation on phase {
                from: 0; to: Math.PI * 2; duration: 1100
                loops: Animation.Infinite
                running: processingIndicator.visible
            }
            Repeater {
                model: 3
                Rectangle {
                    required property int index
                    width: 6; height: 6; radius: 3
                    x: 5 + index * 13
                    y: 6 - 4 * Math.sin(processingIndicator.phase - index * 0.9)
                    opacity: 0.65 + 0.35 * (0.5 + 0.5 * Math.sin(processingIndicator.phase - index * 0.9))
                    color: "#fff4dc"
                }
            }
        }

        MouseArea {
            id: mouseArea
            objectName: "orbMouseArea"
            anchors.fill: parent
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
                if (startRecording) assistant.toggleRecording()
            }
            onCanceled: { overlay.dragging = false; overlay.dragButton = Qt.NoButton; nativeMoving = false }
            onClicked: function(mouse) { if (mouse.button === Qt.RightButton) menu.openAboveOrb() }
        }
    }

    Component.onCompleted: Ui.Theme.dark = assistant.darkTheme

    Connections {
        target: assistant
        function onNotification(message) { assistant.showError(message) }
        function onThemeChanged() { Ui.Theme.dark = assistant.darkTheme }
    }
    Menu {
        id: menu
        objectName: "assistantMenu"
        width: 284
        padding: 6
        popupType: Popup.Window
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        Ui.MenuEntry {
            objectName: "recordingMenuItem"
            iconName: assistant.status === "recording" ? "stop" : "microphone"
            text: assistant.status === "recording" ? "Остановить запись" : assistant.status === "processing" ? "Распознавание…" : assistant.status === "starting" ? "Подготовка микрофона…" : "Голосовой ввод"
            enabled: assistant.status === "idle" || assistant.status === "recording"
            checked: assistant.status === "recording"
            onTriggered: assistant.toggleRecording()
        }
        Ui.MenuDivider {}
        Ui.MenuEntry {
            objectName: "pinMenuItem"
            iconName: "pin"
            text: "Закрепить поверх всех окон"
            checked: assistant.alwaysOnTop
            onTriggered: assistant.toggleAlwaysOnTop()
        }
        Ui.MenuDivider {}
        Ui.MenuEntry { iconName: "note"; text: "Заметки"; onTriggered: assistant.showNotes() }
        Ui.MenuEntry { iconName: "history"; text: "История распознавания"; onTriggered: assistant.showHistory() }
        Ui.MenuEntry { iconName: "settings"; text: "Настройки"; onTriggered: assistant.showSettings() }
        Ui.MenuDivider {}
        Ui.MenuEntry { iconName: "exit"; text: "Выход"; danger: true; onTriggered: assistant.quit() }

        background: Rectangle {
            radius: Ui.Theme.radius
            color: Ui.Theme.surface
            border.color: Ui.Theme.border
            border.width: 1
        }
        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Ui.Theme.motion; easing.type: Easing.OutQuad }
        }
        exit: Transition {
            NumberAnimation { property: "opacity"; from: 1; to: 0; duration: Ui.Theme.motion; easing.type: Easing.InQuad }
        }
        onClosed: overlay.menuFocus = false
        function openAboveOrb() {
            overlay.menuFocus = true
            overlay.requestActivate()
            Qt.callLater(function() { menu.popup(overlay.contentItem, Math.round((overlay.width - menu.width) / 2), -menu.implicitHeight - 12) })
        }
    }
}
