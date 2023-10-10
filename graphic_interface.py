from PyQt5.QtCore import Qt, QRectF, QSizeF, QPointF ,QObject, QRunnable, pyqtSignal, pyqtSlot ,QThreadPool
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QPolygonF
from PyQt5.QtWidgets import (QApplication, QComboBox , QMessageBox ,QLineEdit ,QGraphicsEllipseItem, QHBoxLayout, QGraphicsRectItem, QWidget, QGraphicsView, QGraphicsItem, QGraphicsScene, 
                             QTabWidget, QVBoxLayout, QToolTip,QFileDialog,QPushButton, QLabel,QDialog, QGridLayout ,QTextEdit)
import pandas as pd
import numpy as np
from scipy.spatial import distance
import random
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    """
    error = pyqtSignal(str)
    file_saved_as = pyqtSignal(str)

class Generator(QRunnable):
    def __init__(self, data, filepath):
        super().__init__()
        self.data = data
        self.filepath = filepath
        self.signals = WorkerSignals()

    
    @pyqtSlot()
    def run(self):
        global global_comments
        try:
            c = canvas.Canvas(self.filepath, pagesize=letter)
            width, height = letter

            # Write the title on the first page, centered and slightly above the middle
            c.setFont("Helvetica", 24)
            c.drawCentredString(width / 2, height / 2 + 100, self.data['title'])

            # Start a new page
            c.showPage()

            # Write the rest of the content on the following pages
            c.setFont("Helvetica", 12)
            textobject = c.beginText(50, height - 50)
            lines = self.data['comment'].split('\n')
            for line in lines:
                textobject.textLine(line)
                
            textobject.textLine()  # Add a blank line

            # Additional comments for points and groups
            for identifier, comment in self.data['additional_comments'].items():
                textobject.textLine(f'{identifier}: {comment}')
            
            

            for i, comment in enumerate(global_comments, 1):
                textobject.textLine(f"Comment {i}:")
                textobject.textLine(f"Identifiers: {', '.join(map(str, comment['identifiers']))}")
                textobject.textLine(f"Comment: {comment['comment']}")
                textobject.textLine('')  # Add a blank line
                
                
            
            c.drawText(textobject)

            c.save()
        except Exception as e:
            self.signals.error.emit(str(e))
            return

        self.signals.file_saved_as.emit(self.filepath)
        
class DotColorManager:
    def __init__(self):
        self.colors = [QColor(Qt.red), QColor(Qt.green), QColor(Qt.blue)]  # List of colors

    def get_color(self, value):
        return self.colors[int(value)-1]  # Get color based on value (1-based index)
    
global_comments = []

class CommentDialog(QDialog):
    def __init__(self, identifier, parent=None):
        super().__init__(parent)
        self.identifiers = identifier
        self.layout = QVBoxLayout()
        self.label = QLabel("Write your comment:")
        self.comment_edit = QTextEdit()
        self.submit_button = QPushButton("Submit")
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.comment_edit)
        self.layout.addWidget(self.submit_button)
        self.setLayout(self.layout)
        self.submit_button.clicked.connect(self.submit_comment)

    def submit_comment(self):
        global global_comments  # Reference the global variable
        comment = self.comment_edit.toPlainText()
        # Append the comment to the global variable instead of self.comments1
        global_comments.append({"identifiers": self.identifiers, "comment": comment})
        print(f"Comment for group: {comment}")
        self.close()

    def get_comments(self):
        global global_comments  # Reference the global variable
        return global_comments  # Return the global variable instead of self.comments1
    
class DotItem(QGraphicsEllipseItem):
    def __init__(self, x, y, data, view, col):
        super().__init__(float(x) - 5, float(y) - 5, 10, 10)
        self.view = view
        self.setAcceptHoverEvents(True)
        self.data = data
        self.color_manager = DotColorManager()
        self.setFlag(QGraphicsEllipseItem.ItemIsSelectable)
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable)
        self.setBrush(QBrush(Qt.transparent))  # make the fill transparent
        self.setPen(QPen(self.color_manager.get_color(col)))
        
        self._comment = ''
        
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.view.drag_select_mode:
            event.ignore()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.view.drag_select_mode:
            event.ignore()
        else:
            super().mouseMoveEvent(event)
            
    def mouseDoubleClickEvent(self, event):
        dialog = QDialog()
        layout = QVBoxLayout()
        text_edit = QTextEdit(self._comment)
        button = QPushButton("Save")
        button.clicked.connect(lambda: self._save_comment(text_edit.toPlainText(), dialog))
        layout.addWidget(text_edit)
        layout.addWidget(button)
        dialog.setLayout(layout)
        dialog.exec()
        
    def _save_comment(self, comment, dialog):
          self._comment = comment
          dialog.close()
          
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.view.drag_select_mode:
            event.ignore()
        else:
            super().mouseReleaseEvent(event)
    
    def hoverEnterEvent(self, event):
        tooltip_text = '\n'.join([f'{k}: {v}' for k, v in self.data.items()])
        self.setToolTip(tooltip_text)
        super().hoverEnterEvent(event)
    
    def get_comment_and_coordinates(self):
        return ((self.rect().x(), self.rect().y()), self._comment)
    
    def update_color(self, state):
        self.setBrush(QBrush(self.color_manager.get_color(state)))
        self.setPen(QPen(self.color_manager.get_color(state)))
        
class MyGraphicsView(QGraphicsView):
    def __init__(self, scene, toggle_button):
        super().__init__(scene)
        self.comments = {}  # Add this line
        self.toggle_button = toggle_button
        self.drag_select_mode = False
        self.panning = False
        self.last_mouse_pos = QPointF()
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.HighQualityAntialiasing)
        self.selection_rect_item = QGraphicsRectItem()
        self.selection_rect_item.setPen(QPen(Qt.blue, 2, Qt.DotLine))
        self.selection_rect_item.setBrush(Qt.transparent)
        self.selection_rect_item.setVisible(False)
        self.scene().addItem(self.selection_rect_item)
        self.drag_start_pos = QPointF()
    
    

    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.toggle_button.isChecked():
            self.drag_start_pos = self.mapToScene(event.pos())
            self.selection_rect_item.setRect(QRectF(self.drag_start_pos, QSizeF()))
            self.selection_rect_item.setVisible(True)
        elif event.button() == Qt.RightButton:
            self.panning = True
            self.last_mouse_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.toggle_button.isChecked():
            if not self.drag_start_pos.isNull():
                self.selection_rect_item.setRect(QRectF(self.drag_start_pos, self.mapToScene(event.pos())).normalized())
        elif self.panning:
            delta = self.last_mouse_pos - event.pos()
            self.last_mouse_pos = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + delta.y())
    
        super().mouseMoveEvent(event)
    
    def wheelEvent(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        # Zoom in
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        # Zooming out
        else:
            zoom_factor = zoom_out_factor

        self.scale(zoom_factor, zoom_factor)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.toggle_button.isChecked():
            if not self.drag_start_pos.isNull():
                self.selection_rect_item.setVisible(False)
                polygon = QPolygonF(self.selection_rect_item.rect())
                selected_items = self.scene().items(polygon, Qt.IntersectsItemShape)
                selected_dots = [item for item in selected_items if isinstance(item, DotItem)]
                for dot in selected_dots:
                    dot.setSelected(True)
                    dot.setBrush(QBrush(Qt.red))
                for item in self.scene().items():
                    if isinstance(item, DotItem) and item not in selected_dots:
                        item.setSelected(False)
                        item.setBrush(QBrush(Qt.black))
                print("Selected Dots:", len(selected_dots))
                self.drag_start_pos = QPointF()
                if len(selected_dots) > 1:
                    self.open_comment_dialog()
                    print(self.comment_dialog.get_comments())
                    
        elif event.button() == Qt.RightButton:
            self.panning = False
            self.setCursor(Qt.ArrowCursor)
        else:
            super().mouseReleaseEvent(event)
            
    def open_comment_dialog(self):
        selected_dots = [item for item in self.scene().items() if isinstance(item, DotItem) and item.isSelected()]
        identifiers = [(dot.rect().x(), dot.rect().y()) for dot in selected_dots]
        self.comment_dialog = CommentDialog(identifiers)
        
        self.comment_dialog.show()
        
        
    def collect_dot_comments(self):
        dot_comments = {}
        for item in self.scene().items():
            if isinstance(item, DotItem):
                coordinates, comment = item.get_comment_and_coordinates()
                if comment:  # only include dots that have comments
                    dot_comments[coordinates] = comment
        return dot_comments
    
class CommentWindow(QDialog):
    def __init__(self, comments, parent=None):
        super().__init__(parent)
        self.comments = comments  # And store it as an instance variable here
        self.threadpool = QThreadPool()
        self.setWindowTitle("Print pdf")
        
        self.layout = QVBoxLayout(self)
        
        self.label = QLabel("Title")
        self.layout.addWidget(self.label)
        
        self.textbox = QTextEdit()
        self.layout.addWidget(self.textbox)
        
        self.label2 = QLabel("Comment")
        self.layout.addWidget(self.label2)

        self.textbox2 = QTextEdit()
        self.layout.addWidget(self.textbox2)

        self.button = QPushButton("Print")
        self.button.clicked.connect(self.start_pdf_generation)
        self.layout.addWidget(self.button)

        self.setLayout(self.layout)

    def start_pdf_generation(self):
        

        data = {
            'title': self.textbox.toPlainText(),
            'comment': self.textbox2.toPlainText(),
            'additional_comments': self.comments,
        }
        #print(self.comments)
        filepath = QFileDialog.getSaveFileName(self, 'Save PDF', '', 'PDF Files (*.pdf)')[0]
        if filepath:
            generator = Generator(data, filepath)
            self.threadpool.start(generator)
        
        
    
    
    
    def show_error_message(self, message):
        QMessageBox.critical(self, "Error", message)

    def show_success_message(self, filename):
        QMessageBox.information(self, "Success", f"File saved as {filename}")

        
class MainApp(QWidget):
    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tabs.resize(300, 200)

        self.tabs.addTab(self.tab1, "Tab 1")
        self.tabs.addTab(self.tab2, "Tab 2")

        # For Tab 1
        self.tab1_layout = QVBoxLayout(self.tab1)
        self.label1 = QLabel("Welcome")
        self.combo1 = QComboBox()
        self.combo1.addItem("Option 1")
        self.combo1.addItem("Option 2")
        self.button1_tab1 = QPushButton("Browse file")
        self.button1_tab1.clicked.connect(self.browse_file)  # Connect button click to browse_file function
        self.textbox1 = QLineEdit()
        self.button2_tab1 = QPushButton("Proceed")
        self.button2_tab1.clicked.connect(self.load_dots)
        
        self.tab1_layout.addWidget(self.label1)
        self.tab1_layout.addWidget(self.combo1)
        self.tab1_layout.addWidget(self.button1_tab1)
        self.tab1_layout.addWidget(self.textbox1)
        self.tab1_layout.addWidget(self.button2_tab1)
        

        # For Tab 2
        self.comments = {}  # keep track of comments
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-5000, -5000, 10000, 10000)
        self.toggle_button = QPushButton("Drag Select")
        self.toggle_button.setCheckable(True)
        self.toggle_button.toggled.connect(self.button1_toggle)
        self.button2 = QPushButton("Print PDF")
        self.button2.clicked.connect(self.on_button2_clicked)
        
        self.view = MyGraphicsView(self.scene, self.toggle_button)
        self.tab2_layout = QVBoxLayout(self.tab2)
        self.tab2_layout.addWidget(self.view)

        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.addWidget(self.toggle_button)
        self.buttons_layout.addWidget(self.button2)

        self.tab2_layout.addLayout(self.buttons_layout)
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)


        self.threadpool = QThreadPool()

        

    def button1_toggle(self, checked):
        self.view.drag_select_mode = checked
    
    def show(self):
        super().show()
        self.resize(1000, 600)  # Set the initial window size
    
    def browse_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_name, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", "All Files (*)", options=options)
        if file_name:
            self.textbox1.setText(file_name)  # Set the selected file path to the textbox
            
    def load_dots(self):
        path = self.textbox1.text()
        data = pd.read_csv(path, skipinitialspace=True)
        A = data[['Time', 'Amount']].values.tolist()
        instance = KMeans(A)
        A = instance.process(3)
        for i, row in data.iterrows():
            x = row['Time']
            y = row['Amount']
            self.scene.addItem(DotItem(x, y, row.to_dict(), self.view, A[i, 2]))
        self.tabs.setCurrentIndex(1)  
        
    def on_button2_clicked(self):
        group_comments = self.comments
        dot_comments = self.view.collect_dot_comments()
        #group_comments = self.comment_dialog.get_comments()
        #print(group_comments)
        all_comments = {**group_comments, **dot_comments}
        self.comment_window = CommentWindow(all_comments)
        self.comment_window.show()
    
    
class KMeans:
    def __init__(self, Array):
        self.A = Array
        
    def process(self, k):
        
        def centeroidnp(arr):#calculate centroid 
            length = len(arr)
            arr = np.array(arr)
            sum_x = np.sum(arr[:, 0])
            sum_y = np.sum(arr[:, 1])
            
            return sum_x/length, sum_y/length

        
            
        def dist(A,c2):#distance to the centroid
            A = np.array(A)
            
            for n in range (len(A)):
               # print(A[n,0:2])
                if distance.euclidean(A[n,0:2], c2[0])<distance.euclidean(A[n,0:2], c2[1]) and distance.euclidean(A[n,0:2], c2[0])<distance.euclidean(A[n,0:2], c2[2]):
                    A[n,2]=1
                  #  print("1")
                elif distance.euclidean(A[n,0:2], c2[1])<distance.euclidean(A[n,0:2], c2[0]) and distance.euclidean(A[n,0:2], c2[1])<distance.euclidean(A[n,0:2], c2[2]):
                        A[n,2]=2
                      #  print("2")
                elif distance.euclidean(A[n,0:2], c2[2])<distance.euclidean(A[n,0:2], c2[0]) and distance.euclidean(A[n,0:2], c2[2])<distance.euclidean(A[n,0:2], c2[1]):
                            A[n,2]=3
                           # print("3")
            #print("sss")
            return A

        def arrange(A):#order the points in the array
            c1=[]
            n=1
            for n in range (k+1):
                c1.append([])
                for x in range (len(A)):    
                    if A[x][2]==n:
                        c1[n-1].append(A[x])
            return c1

        def centroid(c1):#compute centroid
            c2=[]   
            for n in range (k):
                c2.append(centeroidnp(c1[n]))
            return c2
               
        for x in range (len(self.A)):#atribute random clusters
            self.A[x].append(random.randint(1,k))
           # print(A[x])
         #   print(A[x][2])

        
        z=0
        y=0
        while z!=1:
            a1=self.A  
            c1=arrange(self.A)
            c2=centroid(c1)        
            self.A=dist(self.A,c2)
            a2=self.A  
            print(y)
            comparison = a1 == a2
            equal_arrays = comparison.all()     
            y=y+1
            if equal_arrays==True:        
                z=z+1       
        
        return self.A   
        
if __name__ == "__main__":
    app = QApplication([])
    main_app = MainApp()
    main_app.show()
    app.exec_()