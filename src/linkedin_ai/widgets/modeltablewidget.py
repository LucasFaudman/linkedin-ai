from typing import Optional, Union, Any

from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from pydantic import BaseModel

from .checkablecombobox import CheckableComboBox


class ClickableTableWidget(qtw.QTableWidget):
    itemsClicked = qtc.pyqtSignal(list)
    rowsClicked = qtc.pyqtSignal(list)

    def mousePressEvent(self, event) -> None:
        items = self.selectedItems()
        if items:
            self.itemsClicked.emit(items)
            # dict.fromkeys preserves order of rows with no duplicates
            self.rowsClicked.emit(list(dict.fromkeys(item.row() for item in items)))
        super().mousePressEvent(event)


class ModelTableWidget(qtw.QWidget):
    itemsClicked = qtc.pyqtSignal(list)
    rowsClicked = qtc.pyqtSignal(list)

    def __init__(
        self,
        data_list: list,
        initial_filters: Optional[dict] = None,
        resize_columns: Optional[Union[list, bool]] = None,
    ) -> None:
        super().__init__()

        self.data_list = data_list
        self.filters = initial_filters or {}
        self.line_edits = {}
        self.resize_columns = resize_columns

        layout = qtw.QVBoxLayout(self)
        keys_to_show_label = qtw.QLabel("Select Columns to Display:")
        self.keys_to_show = CheckableComboBox()
        self.keys_to_show.dataChanged.connect(self.onKeysToShowChanged)
        layout.addWidget(keys_to_show_label)
        layout.addWidget(self.keys_to_show)

        # Create a scroll area
        scroll_area = qtw.QScrollArea()
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # Create table widget
        self.table_widget = ClickableTableWidget()
        self.table_widget.rowsClicked.connect(self.onRowsClicked)
        scroll_area.setWidget(self.table_widget)

        buttons_layout = qtw.QHBoxLayout()
        select_all_button = qtw.QPushButton("Select All")
        select_all_button.clicked.connect(self.select_all)
        buttons_layout.addWidget(select_all_button)
        unselect_all_button = qtw.QPushButton("Unselect All")
        unselect_all_button.clicked.connect(self.unselect_all)
        buttons_layout.addWidget(unselect_all_button)
        remove_selected = qtw.QPushButton("Remove Selected Items")
        remove_selected.clicked.connect(self.remove_selected)
        buttons_layout.addWidget(remove_selected)
        layout.addLayout(buttons_layout)

        # Set up table if data is provided
        if data_list:
            self.reset_keys_to_show()
            self.keys_to_show_initialized = True
            self.update_table(data_list)
        else:
            self.keys_to_show_initialized = False

    def reset_keys_to_show(self) -> None:
        self.keys_to_show.clear()
        if not self.data_list:
            return
        item0 = self.data_list[0]
        if isinstance(item0, BaseModel):
            item0 = item0.model_dump()
        self.keys_to_show.addItems(item0.keys(), checked=True)

    def transform_item_for_table(self, item: Any) -> dict:
        """Transform items to be displayed in the table. Override this method to customize the display of items."""
        if isinstance(item, BaseModel):
            item = item.model_dump()

        return item

    @qtc.pyqtSlot(list)
    def update_table(self, data_list) -> None:
        self.data_list = data_list
        # self.filters = self.get_filters_from_line_edits()
        self.line_edits = {}
        self.filtered_data_list = self.get_filtered_data_list(self.data_list, self.filters)

        if not self.keys_to_show_initialized:
            self.reset_keys_to_show()
            self.keys_to_show_initialized = True
        # Get keys from the first dictionary in the list
        keys = self.keys_to_show.currentData()

        # Set row and column count
        self.table_widget.setRowCount(len(self.filtered_data_list) + 1)  # Add one for filter row
        self.table_widget.setColumnCount(len(keys))

        # Set headers
        self.table_widget.setHorizontalHeaderLabels(keys)
        vertical_headers = [f"{len(self.filtered_data_list)}\ntotal"] + [
            str(i) for i in range(1, len(self.filtered_data_list) + 1)
        ]
        self.table_widget.setVerticalHeaderLabels(vertical_headers)

        for col, key in enumerate(keys):
            line_edit = qtw.QLineEdit(self.table_widget)
            line_edit.setPlaceholderText(f"Filter {key}")
            if key in self.filters:
                line_edit.setText(self.filters[key])
            line_edit.textEdited.connect(self.onFiltersChanged)
            # Place QLineEdit at top of column
            self.table_widget.setCellWidget(0, col, line_edit)
            self.line_edits[key] = line_edit

        # Populate table
        for row, item in enumerate(self.filtered_data_list, 1):
            item = self.transform_item_for_table(item)

            for col, key in enumerate(keys):
                item_widget = qtw.QTableWidgetItem(str(item[key]))
                if col == 0:  # Add checkbox to the first column
                    item_widget.setFlags(item_widget.flags() | qtc.Qt.ItemIsEnabled | qtc.Qt.ItemIsUserCheckable)
                    item_widget.setCheckState(qtc.Qt.Unchecked)

                self.table_widget.setItem(row, col, item_widget)

        # Resize columns to fit contents
        if self.resize_columns is True:
            self.table_widget.resizeColumnsToContents()
        elif self.resize_columns:
            for col_name in self.resize_columns:
                if col_name in keys:
                    col = keys.index(col_name)
                    self.table_widget.resizeColumnToContents(col)

    def get_filters_from_line_edits(self) -> dict:
        filters = {}
        for key, line_edit in self.line_edits.items():
            text = line_edit.text()
            if text:
                filters[key] = text
        return filters

    def get_filtered_data_list(self, data_list, filters) -> list:
        filtered_data_list = []
        for item in data_list:
            item_dict = self.transform_item_for_table(item)

            if all(filter_text in str(item_dict[key]) for key, filter_text in filters.items()):
                filtered_data_list.append(item)
        return filtered_data_list

    @qtc.pyqtSlot()
    def onFiltersChanged(self) -> None:
        new_filters = self.get_filters_from_line_edits()
        changed_filter = None
        for key in new_filters:
            if new_filters[key] != self.filters.get(key):
                changed_filter = key
                break

        self.filters = new_filters
        self.update_table(self.data_list)
        if changed_filter:
            self.line_edits[changed_filter].setFocus()

    @qtc.pyqtSlot(list)
    def onKeysToShowChanged(self, selected_keys) -> None:
        self.update_table(self.data_list)

    @qtc.pyqtSlot(list)
    def onRowsClicked(self, row_indices) -> None:
        self.rowsClicked.emit([self.data_list[i - 1] for i in row_indices])

    @qtc.pyqtSlot(object)
    def append(self, data) -> None:
        self.data_list.append(data)
        self.update_table(self.data_list)

    @qtc.pyqtSlot(object)
    def prepend(self, data) -> None:
        self.data_list.insert(0, data)
        self.update_table(self.data_list)

    @qtc.pyqtSlot(list)
    def extend(self, data_list) -> None:
        self.data_list.extend(data_list)
        self.update_table(self.data_list)

    @qtc.pyqtSlot(list)
    def extend_before(self, data_list) -> None:
        self.data_list = data_list + self.data_list
        self.update_table(self.data_list)

    @qtc.pyqtSlot()
    def clear_table(self) -> None:
        self.table_widget.clearContents()
        self.data_list = []
        self.filtered_data_list = []
        self.keys_to_show_initialized = False
        self.update_table(self.data_list)

    @qtc.pyqtSlot(object)
    def remove_item(self, item) -> None:
        try:
            self.data_list.remove(item)
        except ValueError:
            pass  # Faster than checking if item is in list
        self.update_table(self.data_list)

    @qtc.pyqtSlot(list)
    def remove_items(self, items) -> None:
        for item in items:
            self.data_list.remove(item)
        self.update_table(self.data_list)

    def get_selected_rows(self) -> list:
        selected_rows = []
        for row in range(1, self.table_widget.rowCount()):
            if (
                table_item := self.table_widget.item(row, 0)
            ) and table_item.checkState() == qtc.Qt.Checked:  # Check if checkbox is checked
                # Subtract 1 to account for filter row
                selected_rows.append(self.filtered_data_list[row - 1])
        return selected_rows

    def select_all(self) -> None:
        for row in range(1, self.table_widget.rowCount()):
            if table_item := self.table_widget.item(row, 0):
                table_item.setCheckState(qtc.Qt.Checked)

    def unselect_all(self) -> None:
        for row in range(1, self.table_widget.rowCount()):
            if table_item := self.table_widget.item(row, 0):
                table_item.setCheckState(qtc.Qt.Unchecked)

    def remove_selected(self) -> None:
        self.remove_items(self.get_selected_rows())


if __name__ == "__main__":
    import sys

    app = qtw.QApplication(sys.argv)
    data = [
        {"name": "Alice", "age": 25},
        {"name": "Bob", "age": 30},
        {"name": "Charlie", "age": 35},
    ]

    widget = ModelTableWidget(data)
    widget.show()
    widget.append({"name": "David", "age": 40})
    sys.exit(app.exec_())
