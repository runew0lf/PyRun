import os
import os.path
import subprocess
import sys

from dotenv import load_dotenv
from PyQt5.QtCore import Qt, pyqtSlot, QTimer
from PyQt5.QtGui import QColor, QTextCursor
from PyQt5.QtWidgets import (QAction, QApplication, QDialog, QFileDialog,
                             QMainWindow, QMenu, QStyle, QSystemTrayIcon, qApp)

from Trekho_UI import Ui_dlgTrekho
from Ui_trek_log import Ui_dlgLogs


def getPythonPath(currentpath):
    """
    Gets location of python.exe from current path
    """
    for dirpath, dirnames, filenames in os.walk(currentpath):
        for filename in [f for f in filenames if f.lower() == "pythonw.exe"]:
            return os.path.join(dirpath, filename)
    return "pythonw"


class ApplicationWindow(QMainWindow):
    def __init__(self):
        super(ApplicationWindow, self).__init__()

        self.ui = Ui_dlgTrekho()
        self.ui.setupUi(self)
        self.process_id = {}
        self.originalBG = None

        # Add Capture Events for Buttons
        self.ui.btnExit.clicked.connect(self.on_btnExit)
        self.ui.btnAdd.clicked.connect(self.on_btnAdd)
        self.ui.btnRemove.clicked.connect(self.on_btnRemove)
        self.ui.btnStart.clicked.connect(self.on_btnStart)
        self.ui.btnStop.clicked.connect(self.on_btnStop)

        # Start 6 second time to check if process's are still running
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_process)
        self.timer.start(1000 * 6)

        # Init QSystemTrayIcon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(
            self.style().standardIcon(QStyle.SP_ComputerIcon))
        show_action = QAction("Show", self)
        quit_action = QAction("Exit", self)
        hide_action = QAction("Hide", self)
        show_action.triggered.connect(self.show)
        hide_action.triggered.connect(self.hide)
        quit_action.triggered.connect(qApp.quit)
        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.systemIcon)
        self.tray_icon.show()

        # Listview context menu
        self.ui.listboxFiles.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.listboxFiles.customContextMenuRequested.connect(self.showMenu)

    # Restore view when tray icon doubleclicked
    def systemIcon(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()

    # Check to see what process's are running on the timer and clear the background if complete
    def check_process(self):
        for fname, process in self.process_id.items():
            poll = process.poll()
            if poll is not None:
                for i in range(self.ui.listboxFiles.count()):
                    if self.ui.listboxFiles.item(i).text() == fname:
                        self.ui.listboxFiles.item(
                            i).setBackground(self.originalBG)

    # Show log dialog
    def showLog(self):
        dlgLog = QDialog(self)
        ui = Ui_dlgLogs()
        ui.setupUi(dlgLog)
        full_path = str(self.ui.listboxFiles.currentItem().text())
        std_out = open(f"{full_path}.log", "r")
        filename = os.path.basename(full_path)
        text = std_out.readlines()
        ui.textEdit.setText("\n".join(text))
        dlgLog.setWindowTitle(f"{filename} - Log")
        dlgLog.show()
        ui.textEdit.moveCursor(QTextCursor.End)
        dlgLog.exec_()

    # Add right-click context menu for the listview
    def showMenu(self, pos):
        menu = QMenu()
        exploreAction = menu.addAction("Open in explorer")
        showlogAction = menu.addAction("Show Logfile")
        action = menu.exec_(self.ui.listboxFiles.viewport().mapToGlobal(pos))
        if action == exploreAction:
            full_path = str(self.ui.listboxFiles.currentItem().text())
            dir_path = os.path.dirname(os.path.abspath(full_path))
            os.startfile(dir_path)
        if action == showlogAction:
            self.showLog()

    # Override closeEvent, to intercept the window closing event
    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Tray Program",
            "Application was minimized to Tray",
            QSystemTrayIcon.Information,
            2000
        )

    def addFiles(self, files):
        files = map(lambda s: s.strip(), files)
        self.ui.listboxFiles.addItems(files)

    @pyqtSlot()
    def on_btnExit(self):
        self.tray_icon.hide()
        for fname, process in self.process_id.items():
            poll = process.poll()
            if poll is None:
                self.process.terminate()
        exit(0)

    @pyqtSlot()
    def on_btnStop(self):
        self.ui.listboxFiles.currentItem().setBackground(self.originalBG)
        filename = self.ui.listboxFiles.currentItem().text()
        # Check to see if process is still running before we terminate it
        poll = self.process_id[filename].poll()
        if poll is None:
            self.process_id[filename].terminate()
        print("Stopped")

    @pyqtSlot()
    def on_btnStart(self):
        print("started")
        self.originalBG = self.ui.listboxFiles.currentItem().background()

        full_path = str(self.ui.listboxFiles.currentItem().text())
        self.ui.listboxFiles.currentItem().setBackground(QColor('#7fc97f'))
        dir_path = os.path.dirname(os.path.abspath(full_path))
        with open(f"{full_path}.log", "w") as std_out:
            env_path = f"{dir_path}/.env"
            load_dotenv(dotenv_path=env_path)
            process_id = subprocess.Popen([f"{getPythonPath(dir_path)}",
                                           str(self.ui.listboxFiles.currentItem().text())],
                                          stdout=std_out,
                                          cwd=dir_path)
            self.process_id[full_path] = process_id

    @pyqtSlot()
    def on_btnRemove(self):
        a_list = self.ui.listboxFiles.selectedItems()
        for item in a_list:
            self.ui.listboxFiles.takeItem(self.ui.listboxFiles.row(item))
        with open("file.txt", "w") as fh:
            itemsTextList = [str(self.ui.listboxFiles.item(i).text())
                             for i in range(self.ui.listboxFiles.count())]
            fh.write("\n".join(itemsTextList))

    @pyqtSlot()
    def on_btnAdd(self):
        filename = self.openFileNameDialog()
        self.ui.listboxFiles.addItem(filename)
        with open("file.txt", "w") as fh:
            itemsTextList = [str(self.ui.listboxFiles.item(i).text())
                             for i in range(self.ui.listboxFiles.count())]
            fh.write("\n".join(itemsTextList))

    def openFileNameDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(
            self, "QFileDialog.getOpenFileName()", "", "All Files (*);;Python Files (*.py)", options=options)
        if fileName:
            return fileName


def main():
    with open("file.txt", "r") as fh:
        files = fh.readlines()
    app = QApplication(sys.argv)
    application = ApplicationWindow()
    application.addFiles(files)
    application.show()
    try:
        sys.exit(app.exec_())
    except SystemExit:
        pass


if __name__ == "__main__":
    main()
