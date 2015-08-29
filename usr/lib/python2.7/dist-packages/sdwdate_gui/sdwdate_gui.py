#! /usr/bin/env python

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import QFileSystemWatcher as watcher
from PyQt4.QtCore import QThread
import subprocess
from subprocess import check_output, call
import pickle
import os
import time


class RightClickMenu(QtGui.QMenu):

    def __init__(self, parent=None):
        QtGui.QMenu.__init__(self, "File", parent)

        icon = QtGui.QIcon('/usr/share/icons/oxygen/16x16/mimetypes/text-x-script.png')
        action = QtGui.QAction(icon, "Open sdwdate's log", self)
        action.triggered.connect(show_log)
        self.addAction(action)

        self.addSeparator()

        icon = QtGui.QIcon('/usr/share/icons/oxygen/16x16/actions/system-reboot.png')
        text = 'Restart sdwdate - Gradually adjust the time'
        action = QtGui.QAction(icon, text, self)
        action.triggered.connect(restart_sdwdate)
        self.addAction(action)

        icon = QtGui.QIcon('/usr/share/icons/oxygen/16x16/actions/system-reboot.png')
        text = 'Restart sdwdate - Instantly adjust the time.'
        action = QtGui.QAction(icon, text, self)
        action.triggered.connect(restart_fresh)
        self.addAction(action)

        icon = QtGui.QIcon('/usr/share/icons/oxygen/16x16/actions/system-shutdown.png')
        action = QtGui.QAction(icon, "Stop sdwdate", self)
        action.triggered.connect(stop_sdwdate)
        self.addAction(action)

        icon = QtGui.QIcon('/usr/share/icons/oxygen/16x16/actions/application-exit.png')
        action = QtGui.QAction(icon, "&Exit", self)
        action.triggered.connect(QtGui.qApp.quit)
        self.addAction(action)


class Update(QtCore.QObject):
    update_tip = QtCore.pyqtSignal()


## Started by left click action.
## Set message_showing for the default time
## the balloon is displayed (10 seconds).
class MessageStatus(QThread):
    message_status = QtCore.pyqtSignal(bool)
    showing = False

    def run(self):
        self.showing = True
        self.message_status.emit(True)
        while self.showing:
            time.sleep(10)
            self.message_status.emit(False)
            self.showing = False


class SdwdateTrayIcon(QtGui.QSystemTrayIcon):

    def __init__(self, parent=None):
        QtGui.QSystemTrayIcon.__init__(self, parent)

        self.title = 'Time Synchronisation Monitor'
        self.right_click_menu = RightClickMenu()
        self.setContextMenu(self.right_click_menu)

        self.path = '/var/run/sdwdate'
        self.status_path = '/var/run/sdwdate/status'
        self.message = ''

        self.update = Update(self)
        self.update.update_tip.connect(self.update_tip)

        self.message_status = MessageStatus(self)
        self.message_status.message_status.connect(self.update_message_status)
        self.message_showing = False

        self.activated.connect(self.show_message)
        self.messageClicked.connect(self.message_clicked)

        if os.path.exists(self.status_path):
            ## Read status when GUI is loaded.
            self.status_changed()
            self.setToolTip('%s\n%s' %(self.title, self.message))
            self.watcher = watcher([self.status_path])
            self.watcher.fileChanged.connect(self.status_changed)
        else:
            self.setIcon(QtGui.QIcon('/usr/share/icons/oxygen/16x16/status/dialog-error.png'))
            msg = ('%s\n' %(self.title) +
                   'sdwdate not running\n' +
                   'Try to restart it: Right click -> Restart sdwdate\n' +
                   'If the icon stays red, please report this bug.')
            self.message = msg
            self.setToolTip(msg)
            self.watcher_2 = watcher([self.path])
            self.watcher_2.directoryChanged.connect(self.watch_folder)

    def show_message(self, reason):
        if reason == self.Trigger: # left click
            self.message_status.start()
            self.showMessage(self.title, self.message)

    ## The balloon is closed on left click.
    ## Forbid showing again.
    def message_clicked(self):
        self.message_status.quit()
        self.message_showing = False

    ## Signal generated in MessageStatus.
    def update_message_status(self, is_showing):
        self.message_showing = is_showing

    def update_tip(self):
        ## Update tooltip if mouse on icon.
        if self.geometry().contains(QtGui.QCursor.pos()):
            QtGui.QToolTip.showText(QtGui.QCursor.pos(),
                                    '%s\n%s' %(self.title, self.message))
        ## Update balloon message if it's already shown.
        if self.message_showing:
            self.showMessage(self.title, self.message)

    def status_changed(self):
        ## Prevent race condition.
        time.sleep(0.01)
        with open(self.status_path, 'rb') as f:
            status = pickle.load(f)

        self.setIcon(QtGui.QIcon(status['icon']))
        self.message = status['message']
        self.setToolTip('%s\n%s' %(self.title, self.message))
        self.update.update_tip.emit()

    def watch_folder(self):
        self.watcher = watcher([self.status_path])
        self.watcher.fileChanged.connect(self.status_changed)


def show_log():
    cmd = ('konsole --hold --hide-menubar --hide-tabbar ' +
           '-e "tail -f -n 100 /var/log/sdwdate.log"')
    call(cmd, shell=True)

def restart_sdwdate():
    call('sudo service sdwdate restart', shell=True)

def restart_fresh():
    call('sudo rm /var/run/sdwdate/success', shell=True)
    call('sudo service sdwdate restart', shell=True)

def stop_sdwdate():
    call('sudo service sdwdate stop', shell=True)

def main():
    app = QtGui.QApplication([])
    sdwdate_tray = SdwdateTrayIcon()
    sdwdate_tray.show()
    app.exec_()

if __name__ == "__main__":
    main()