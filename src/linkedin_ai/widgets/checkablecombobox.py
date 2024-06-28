from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtGui as qtg


class CheckableComboBox(qtw.QComboBox):
    dataChanged = qtc.pyqtSignal(list)

    # Subclass Delegate to increase item height
    class Delegate(qtw.QStyledItemDelegate):
        def sizeHint(self, option, index):
            size = super().sizeHint(option, index)
            size.setHeight(20)
            return size

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make the combo editable to set a custom text, but readonly
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        # Make the lineedit the same color as QPushButton
        palette = qtw.qApp.palette()
        palette.setBrush(qtg.QPalette.Base, palette.button())
        self.lineEdit().setPalette(palette)

        # Use custom delegate
        self.setItemDelegate(CheckableComboBox.Delegate())

        # Update the text when an item is toggled
        self.model().dataChanged.connect(self.updateText)
        self.model().dataChanged.connect(self.onDataChanged)

        # Hide and show popup when clicking the line edit
        self.lineEdit().installEventFilter(self)
        self.closeOnLineEditClick = False

        # Prevent popup from closing when clicking on an item
        self.view().viewport().installEventFilter(self)

    def resizeEvent(self, event):
        # Recompute text to elide as needed
        self.updateText()
        super().resizeEvent(event)

    def eventFilter(self, obj, event):
        if obj == self.lineEdit():
            if event.type() == qtc.QEvent.MouseButtonRelease:
                if self.closeOnLineEditClick:
                    self.hidePopup()
                else:
                    self.showPopup()
                return True
            return False

        if obj == self.view().viewport():
            if event.type() == qtc.QEvent.MouseButtonRelease:
                index = self.view().indexAt(event.pos())
                item = self.model().item(index.row())

                if item.checkState() == qtc.Qt.Checked:
                    item.setCheckState(qtc.Qt.Unchecked)
                else:
                    item.setCheckState(qtc.Qt.Checked)
                return True
        return False

    def showPopup(self):
        super().showPopup()
        # When the popup is displayed, a click on the lineedit should close it
        self.closeOnLineEditClick = True

    def hidePopup(self):
        super().hidePopup()
        # Used to prevent immediate reopening when clicking on the lineEdit
        self.startTimer(100)
        # Refresh the display text when closing
        self.updateText()

    def timerEvent(self, event):
        # After timeout, kill timer, and reenable click on line edit
        self.killTimer(event.timerId())
        self.closeOnLineEditClick = False

    def updateText(self):
        texts = []
        for i in range(self.model().rowCount()):
            if self.model().item(i).checkState() == qtc.Qt.Checked:
                texts.append(self.model().item(i).text())
        text = ", ".join(texts)

        # Compute elided text (with "...")

        metrics = qtg.QFontMetrics(self.lineEdit().font())
        elidedText = metrics.elidedText(text, qtc.Qt.ElideRight, self.lineEdit().width())
        self.lineEdit().setText(elidedText)

    def addItem(self, text, userData=None, checked=False):
        item = qtg.QStandardItem()
        item.setText(text)
        if userData is None:
            item.setData(text)
        else:
            item.setData(userData)
        item.setFlags(qtc.Qt.ItemIsEnabled | qtc.Qt.ItemIsUserCheckable)
        item.setData(qtc.Qt.Checked if checked else qtc.Qt.Unchecked, qtc.Qt.CheckStateRole)
        self.model().appendRow(item)

    def addItems(self, texts, datalist=None, checked=False):
        for i, text in enumerate(texts):
            try:
                userData = datalist[i] if datalist else None
            except (TypeError, IndexError):
                userData = None
            self.addItem(text, userData, checked)

    def removeItem(self, text):
        for i in range(self.model().rowCount()):
            if self.model().item(i).text() == text:
                self.model().removeRow(i)
                break

    def removeItems(self, texts):
        for text in texts:
            self.removeItem(text)

    def clear(self):
        for i in range(self.model().rowCount()):
            self.model().removeRow(i)

    def currentData(self):
        # Return the list of selected items data
        res = []
        for i in range(self.model().rowCount()):
            if self.model().item(i).checkState() == qtc.Qt.Checked:
                res.append(self.model().item(i).data())
        return res

    def onDataChanged(self):
        self.dataChanged.emit(self.currentData())
