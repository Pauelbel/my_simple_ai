pragma Singleton
import QtQuick
QtObject {
    property bool dark: true
    readonly property color background: dark ? "#181a1d" : "#ffffff"
    readonly property color sidebar: dark ? "#15171a" : "#f7f8fa"
    readonly property color surface: dark ? "#202327" : "#f1f3f6"
    readonly property color hover: dark ? "#282c32" : "#e9edf2"
    readonly property color pressed: dark ? "#313740" : "#dce3ed"
    readonly property color selected: dark ? "#242c38" : "#edf2fa"
    readonly property color border: dark ? "#30343a" : "#e1e5ea"
    readonly property color text: dark ? "#e2e5e9" : "#252a32"
    readonly property color muted: dark ? "#969eaa" : "#667180"
    readonly property color disabled: dark ? "#555d68" : "#b1b8c3"
    readonly property color accent: dark ? "#96b6f1" : "#4269a8"
    readonly property color danger: dark ? "#e7a4a4" : "#ac4444"
    readonly property string family: Qt.platform.os === "windows" ? "Segoe UI" : "Noto Sans"
    readonly property int fontSize: 13
    readonly property int smallFont: 11
    readonly property int documentFont: 16
    readonly property int headingFont: 15
    readonly property int radius: 5
    readonly property int buttonSize: 34
    readonly property int iconSize: 19
    readonly property int rowHeight: 30
    readonly property int barHeight: 54
    readonly property int space: 8
    readonly property int panelPadding: 12
    readonly property int documentPadding: 32
    readonly property int indent: 9
    readonly property int treeInset: 4
    readonly property int treeToggleWidth: 18
    readonly property int motion: 100
}
