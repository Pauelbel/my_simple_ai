import QtQuick

Item {
    id: processingIndicator
    objectName: "processingIndicator"
    width: 42; height: 18
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
