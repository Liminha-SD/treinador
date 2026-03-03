import os
import shutil
import time
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QScrollArea, QPushButton, QFileDialog, QSlider, QLabel, QFrame,
    QMessageBox, QGridLayout, QMenu, QStatusBar, QInputDialog, QProgressBar,
    QLineEdit
)
from PySide6.QtGui import QPixmap, QImage, QColor, QFont, QAction, QDragEnterEvent, QDropEvent
from PySide6.QtCore import Qt, Signal, QRunnable, QThreadPool, Slot, QObject, QSize

# --- Configurações de Performance e Estética ---
MAX_THREADS = os.cpu_count() or 4
COLOR_ACCENT = "#019DEA"
COLOR_BG = "#050505"
COLOR_SURFACE = "#121212"
COLOR_CARD = "#181818"
COLOR_TEXT = "#E0E0E0"
COLOR_TEXT_DIM = "#666666"

IMAGE_EXTS = {'.jpg', '.png', '.jpeg', '.webp', '.bmp', '.jfif'}

# --- Worker de Carregamento de Imagens ---
class WorkerSignals(QObject):
    finished = Signal(str, QPixmap)
    train_progress = Signal(int, str) # Progresso (0-100), Mensagem
    train_finished = Signal(str)      # Caminho do modelo salvo
    train_error = Signal(str)         # Mensagem de erro

class ImageLoaderWorker(QRunnable):
    def __init__(self, file_path, size):
        super().__init__()
        self.file_path = file_path
        self.size = size
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            image = QImage(self.file_path)
            if not image.isNull():
                scaled = image.scaled(self.size * 2, self.size * 2, Qt.KeepAspectRatio, Qt.FastTransformation)
                pixmap = QPixmap.fromImage(scaled)
                self.signals.finished.emit(self.file_path, pixmap)
        except: pass

# --- Worker de Treinamento (TensorFlow) ---
class TrainingWorker(QRunnable):
    def __init__(self, model_name, epochs=10):
        super().__init__()
        self.model_name = model_name
        self.epochs = epochs
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            # Importação Lazy para não pesar na inicialização da GUI
            self.signals.train_progress.emit(5, "Carregando TensorFlow...")
            import tensorflow as tf
            from tensorflow.keras import layers, models

            base_dir = Path(".")
            img_height, img_width = 180, 180
            batch_size = 32

            # Verificar dados
            good_count = len(list(Path("good").glob("*")))
            bad_count = len(list(Path("bad").glob("*")))
            
            if good_count == 0 or bad_count == 0:
                raise Exception(f"Dados insuficientes! Boas: {good_count}, Ruins: {bad_count}. Adicione imagens em ambas.")

            self.signals.train_progress.emit(10, "Criando Datasets...")
            
            # Criar Dataset
            train_ds = tf.keras.utils.image_dataset_from_directory(
                base_dir,
                validation_split=0.2,
                subset="training",
                seed=123,
                image_size=(img_height, img_width),
                batch_size=batch_size,
                class_names=['bad', 'good'] # Ordem alfabética é padrão do TF, mas forçamos para garantir
            )
            
            val_ds = tf.keras.utils.image_dataset_from_directory(
                base_dir,
                validation_split=0.2,
                subset="validation",
                seed=123,
                image_size=(img_height, img_width),
                batch_size=batch_size,
                class_names=['bad', 'good']
            )

            # Otimização de I/O
            AUTOTUNE = tf.data.AUTOTUNE
            train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
            val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)

            self.signals.train_progress.emit(20, "Construindo Modelo...")

            # Arquitetura CNN Simples e Eficiente
            model = models.Sequential([
                layers.Rescaling(1./255, input_shape=(img_height, img_width, 3)),
                layers.Conv2D(16, 3, padding='same', activation='relu'),
                layers.MaxPooling2D(),
                layers.Conv2D(32, 3, padding='same', activation='relu'),
                layers.MaxPooling2D(),
                layers.Conv2D(64, 3, padding='same', activation='relu'),
                layers.MaxPooling2D(),
                layers.Flatten(),
                layers.Dense(128, activation='relu'),
                layers.Dense(1, activation='sigmoid') # Saída binária (0=bad, 1=good)
            ])

            model.compile(optimizer='adam',
                          loss='binary_crossentropy',
                          metrics=['accuracy'])

            # Callback Customizado para atualizar GUI
            class ProgressCallback(tf.keras.callbacks.Callback):
                def __init__(self, signals, total_epochs):
                    self.signals = signals
                    self.total_epochs = total_epochs

                def on_epoch_end(self, epoch, logs=None):
                    percent = 20 + int(((epoch + 1) / self.total_epochs) * 70)
                    acc = logs.get('accuracy', 0)
                    self.signals.train_progress.emit(percent, f"Época {epoch+1}/{self.total_epochs} - Acc: {acc:.2f}")

            self.signals.train_progress.emit(25, "Iniciando Treinamento...")
            
            history = model.fit(
                train_ds,
                validation_data=val_ds,
                epochs=self.epochs,
                callbacks=[ProgressCallback(self.signals, self.epochs)],
                verbose=0
            )

            self.signals.train_progress.emit(95, "Salvando Modelo...")
            save_path = f"{self.model_name}.keras"
            model.save(save_path)
            
            self.signals.train_progress.emit(100, "Concluído!")
            self.signals.train_finished.emit(save_path)

        except ImportError:
            self.signals.train_error.emit("TensorFlow não instalado. Rode: pip install tensorflow")
        except Exception as e:
            self.signals.train_error.emit(str(e))

class ImageWidget(QFrame):
    clicked = Signal(str, bool)

    def __init__(self, file_path, size=150):
        super().__init__()
        self.setObjectName("ImageCard")
        self.file_path = str(file_path)
        self.selected = False
        self.current_size = size
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background: #0A0A0A; border-radius: 6px;")
        layout.addWidget(self.image_label)
        
        name = Path(file_path).name
        self.name_label = QLabel(name if len(name) < 20 else name[:17]+"...")
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet(f"font-size: 10px; color: {COLOR_TEXT_DIM}; border: none; background: transparent;")
        layout.addWidget(self.name_label)
        
        self.setFixedSize(size + 12, size + 45)
        self.setCursor(Qt.PointingHandCursor)

    def set_pixmap(self, pixmap):
        scaled = pixmap.scaled(self.current_size, self.current_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)
        self.image_label.setStyleSheet("background: transparent;")

    def update_size(self, size):
        self.current_size = size
        self.setFixedSize(size + 12, size + 45)
        if self.image_label.pixmap():
            self.set_pixmap(self.image_label.pixmap())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected = not self.selected
            self.setProperty("selected", self.selected)
            self.style().unpolish(self)
            self.style().polish(self)
            self.clicked.emit(self.file_path, self.selected)

class ImageTrainerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Trainer Studio Ultimate")
        self.resize(1350, 900)
        self.setAcceptDrops(True)
        
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(MAX_THREADS)
        
        self.image_widgets = {}
        self.selected_paths = set()
        self.current_image_size = 150
        
        for p in ["good", "bad"]: Path(p).mkdir(exist_ok=True)
        
        self.setup_ui()
        self.setStyleSheet(self.get_main_style())

    def get_main_style(self):
        return f"""
        QMainWindow {{ background-color: {COLOR_BG}; }}
        QWidget {{ background-color: {COLOR_BG}; color: {COLOR_TEXT}; }}
        
        QScrollArea {{ border: none; background-color: {COLOR_BG}; }}
        QScrollArea > QWidget > QWidget {{ background-color: {COLOR_BG}; }}
        
        QScrollBar:vertical {{ border: none; background: #0A0A0A; width: 10px; }}
        QScrollBar::handle:vertical {{ background: #222; border-radius: 5px; }}
        QScrollBar::handle:vertical:hover {{ background: {COLOR_ACCENT}; }}

        /* MENUS & DIALOGS */
        QMenu {{ background-color: {COLOR_SURFACE}; border: 1px solid #333; }}
        QMenu::item:selected {{ background-color: {COLOR_ACCENT}; color: white; }}
        
        QInputDialog, QMessageBox {{ background-color: {COLOR_SURFACE}; color: white; }}
        QLineEdit {{ 
            background: #222; border: 1px solid #444; color: white; padding: 5px; border-radius: 4px;
        }}

        /* BUTTONS */
        QPushButton {{
            background-color: {COLOR_SURFACE}; border: 1px solid #2A2A2A;
            border-radius: 8px; padding: 10px 18px; font-weight: bold; font-size: 12px;
        }}
        QPushButton:hover {{ background-color: #1A1A1A; border-color: {COLOR_ACCENT}; }}
        
        QPushButton#BtnMain {{ background-color: {COLOR_ACCENT}; color: white; border: none; }}
        QPushButton#BtnMain:hover {{ background-color: #0082BD; }}
        QPushButton#BtnMain::menu-indicator {{ image: none; }} 

        QPushButton#BtnTrain {{ 
            background-color: #E0E0E0; color: #000; border: none; font-weight: 900;
        }}
        QPushButton#BtnTrain:hover {{ background-color: white; }}

        QPushButton#BtnGood {{ color: #4CAF50; border-color: #1E351F; }}
        QPushButton#BtnGood:hover {{ background-color: #0F2110; }}

        QPushButton#BtnBad {{ color: #FF5252; border-color: #3D1E1E; }}
        QPushButton#BtnBad:hover {{ background-color: #240F0F; }}

        QPushButton#BtnGhost {{ color: {COLOR_TEXT_DIM}; border: none; background: transparent; font-size: 11px; }}
        QPushButton#BtnGhost:hover {{ color: white; background: #111; }}

        QFrame#ImageCard {{ background-color: {COLOR_CARD}; border: 1px solid #222; border-radius: 10px; }}
        QFrame#ImageCard:hover {{ border-color: #444; }}
        QFrame#ImageCard[selected="true"] {{ border-color: {COLOR_ACCENT}; background-color: #0D1B2A; }}

        QSlider::handle:horizontal {{ background: {COLOR_ACCENT}; width: 14px; margin: -5px 0; border-radius: 7px; }}
        
        QProgressBar {{
            border: 1px solid #333; border-radius: 5px; text-align: center; color: white; background: #111;
        }}
        QProgressBar::chunk {{ background-color: {COLOR_ACCENT}; width: 10px; }}
        QStatusBar {{ background: {COLOR_SURFACE}; border-top: 1px solid #222; color: #888; }}
        """

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(35, 30, 35, 20)
        layout.setSpacing(25)

        # --- HEADER ---
        header = QHBoxLayout()
        
        brand = QVBoxLayout()
        title = QLabel("AI TRAINER STUDIO")
        title.setStyleSheet("font-size: 26px; font-weight: 900; color: white; letter-spacing: -1px; background: transparent;")
        self.status_info = QLabel("Classifique imagens e treine seu modelo")
        self.status_info.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-size: 13px; background: transparent;")
        brand.addWidget(title)
        brand.addWidget(self.status_info)
        
        header.addLayout(brand)
        header.addStretch()

        # Botão Importar
        self.btn_import = QPushButton("IMPORTAR")
        self.btn_import.setObjectName("BtnMain")
        import_menu = QMenu(self)
        import_menu.addAction("Arquivos", self.import_files)
        import_menu.addAction("Pasta", self.import_folder)
        self.btn_import.setMenu(import_menu)
        header.addWidget(self.btn_import)
        
        # Botão TREINAR (Destaque)
        self.btn_train = QPushButton("⚡ TREINAR MODELO")
        self.btn_train.setObjectName("BtnTrain")
        self.btn_train.setCursor(Qt.PointingHandCursor)
        self.btn_train.clicked.connect(self.start_training_dialog)
        header.addWidget(self.btn_train)

        # Zoom
        zoom_wrap = QVBoxLayout()
        zoom_label = QLabel("ZOOM")
        zoom_label.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-size: 9px; font-weight: bold; background: transparent;")
        zoom_label.setAlignment(Qt.AlignCenter)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(80, 400)
        self.slider.setValue(150)
        self.slider.setFixedWidth(100)
        self.slider.valueChanged.connect(self.on_slider_move)
        zoom_wrap.addWidget(zoom_label)
        zoom_wrap.addWidget(self.slider)
        header.addLayout(zoom_wrap)
        
        layout.addLayout(header)

        # --- GRID AREA ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.container.setObjectName("GridContainer")
        self.grid = QGridLayout(self.container)
        self.grid.setSpacing(18)
        self.grid.setContentsMargins(0, 0, 15, 0)
        self.grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        # --- FOOTER ---
        footer = QHBoxLayout()
        
        # Grupo Esquerda
        btn_clear_grid = QPushButton("Limpar Grade")
        btn_clear_grid.setObjectName("BtnGhost")
        btn_clear_grid.clicked.connect(self.clear_grid)
        footer.addWidget(btn_clear_grid)
        
        footer.addStretch()

        # Grupo Centro (Pastas)
        btn_reset_bad = QPushButton("Reset Ruins")
        btn_reset_bad.setObjectName("BtnGhost")
        btn_reset_bad.clicked.connect(lambda: self.clear_disk("bad"))
        
        btn_reset_good = QPushButton("Reset Boas")
        btn_reset_good.setObjectName("BtnGhost")
        btn_reset_good.clicked.connect(lambda: self.clear_disk("good"))
        footer.addWidget(btn_reset_bad)
        footer.addWidget(btn_reset_good)
        
        footer.addStretch()

        # Grupo Direita (Ações)
        self.btn_bad = QPushButton("PARA RUINS")
        self.btn_bad.setObjectName("BtnBad")
        self.btn_bad.setFixedWidth(160)
        self.btn_bad.clicked.connect(lambda: self.process_batch("bad"))

        self.btn_good = QPushButton("PARA BOAS")
        self.btn_good.setObjectName("BtnGood")
        self.btn_good.setFixedWidth(160)
        self.btn_good.clicked.connect(lambda: self.process_batch("good"))

        footer.addWidget(self.btn_bad)
        footer.addWidget(self.btn_good)
        
        layout.addLayout(footer)

        # Progress Bar (Inicialmente oculta)
        self.pbar = QProgressBar()
        self.pbar.setVisible(False)
        self.pbar.setFixedHeight(10)
        layout.addWidget(self.pbar)
        
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Pronto.")

    # --- TRAINING LOGIC ---
    def start_training_dialog(self):
        # 1. Verificar se há dados
        good_c = len(list(Path("good").glob("*")))
        bad_c = len(list(Path("bad").glob("*")))
        
        if good_c < 5 or bad_c < 5:
            QMessageBox.warning(self, "Dados Insuficientes", 
                                f"Você precisa de pelo menos 5 imagens em cada pasta.\n\nBoas: {good_c}\nRuins: {bad_c}")
            return

        # 2. Pedir Nome
        name, ok = QInputDialog.getText(self, "Treinar Modelo", "Nome do arquivo (sem extensão):")
        if ok and name:
            self.run_training(name)

    def run_training(self, name):
        self.btn_train.setEnabled(False)
        self.pbar.setValue(0)
        self.pbar.setVisible(True)
        self.statusBar().showMessage("Inicializando motor TensorFlow...")
        
        worker = TrainingWorker(name, epochs=10)
        worker.signals.train_progress.connect(self.update_train_progress)
        worker.signals.train_finished.connect(self.on_train_finished)
        worker.signals.train_error.connect(self.on_train_error)
        
        self.thread_pool.start(worker)

    def update_train_progress(self, val, msg):
        self.pbar.setValue(val)
        self.statusBar().showMessage(msg)

    def on_train_finished(self, path):
        self.btn_train.setEnabled(True)
        self.pbar.setVisible(False)
        self.statusBar().showMessage("Treinamento concluído.")
        QMessageBox.information(self, "Sucesso", f"Modelo treinado e salvo com sucesso:\n\n{path}")

    def on_train_error(self, err):
        self.btn_train.setEnabled(True)
        self.pbar.setVisible(False)
        self.statusBar().showMessage("Erro no treinamento.")
        QMessageBox.critical(self, "Erro de Treinamento", f"Falha ao treinar:\n{err}")

    # --- STANDARD APP LOGIC ---
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        paths = []
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_dir():
                paths.extend([str(f) for f in p.iterdir() if f.suffix.lower() in IMAGE_EXTS])
            elif p.suffix.lower() in IMAGE_EXTS:
                paths.append(str(p))
        if paths: self.add_images(paths)

    def import_files(self):
        f, _ = QFileDialog.getOpenFileNames(self, "Selecionar Imagens", "", "Imagens (*.jpg *.png *.webp *.jpeg *.bmp)")
        if f: self.add_images(f)

    def import_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Selecionar Pasta")
        if d:
            paths = [str(p) for p in Path(d).iterdir() if p.suffix.lower() in IMAGE_EXTS]
            self.add_images(paths)

    def add_images(self, paths):
        for p in paths:
            if p not in self.image_widgets:
                w = ImageWidget(p, self.current_image_size)
                w.clicked.connect(self.on_click)
                self.image_widgets[p] = w
                worker = ImageLoaderWorker(p, 150)
                worker.signals.finished.connect(self.on_load_finished)
                self.thread_pool.start(worker)
        self.reorganize_grid()
        self.update_status()

    def on_load_finished(self, path, pixmap):
        if path in self.image_widgets:
            self.image_widgets[path].set_pixmap(pixmap)

    def reorganize_grid(self):
        width = self.scroll.width() - 30
        cols = max(1, width // (self.current_image_size + 30))
        for i in reversed(range(self.grid.count())):
            item = self.grid.itemAt(i)
            if item.widget(): item.widget().setParent(None)
        for i, widget in enumerate(self.image_widgets.values()):
            self.grid.addWidget(widget, i // cols, i % cols)
            widget.setParent(self.container)

    def on_slider_move(self):
        self.current_image_size = self.slider.value()
        for w in self.image_widgets.values(): w.update_size(self.current_image_size)
        self.reorganize_grid()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reorganize_grid()

    def clear_grid(self):
        if not self.image_widgets: return
        for w in self.image_widgets.values(): w.deleteLater()
        self.image_widgets.clear()
        self.selected_paths.clear()
        self.update_status()
        self.reorganize_grid()

    def on_click(self, path, sel):
        if sel: self.selected_paths.add(path)
        else: self.selected_paths.discard(path)
        self.update_status()

    def update_status(self):
        total = len(self.image_widgets)
        sel = len(self.selected_paths)
        self.status_info.setText(f"{total} imagens no grid | {sel} selecionadas")

    def process_batch(self, folder):
        if not self.selected_paths: return
        dest = Path(folder)
        count = 0
        for p in list(self.selected_paths):
            try:
                src = Path(p)
                target = dest / src.name
                if target.exists(): target = dest / f"{src.stem}_{int(src.stat().st_mtime)}{src.suffix}"
                shutil.copy2(src, target)
                w = self.image_widgets.pop(p)
                w.deleteLater()
                count += 1
            except: pass
        self.selected_paths.clear()
        self.reorganize_grid()
        self.update_status()
        self.statusBar().showMessage(f"Sucesso: {count} imagens processadas.", 3000)

    def clear_disk(self, folder):
        msg = QMessageBox(self)
        msg.setWindowTitle("Limpar Pasta")
        msg.setText(f"Deseja apagar permanentemente todos os arquivos em '{folder}'?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        if msg.exec() == QMessageBox.Yes:
            for f in Path(folder).iterdir(): 
                if f.is_file(): f.unlink()
            self.statusBar().showMessage(f"Pasta {folder} zerada.", 2000)

if __name__ == "__main__":
    app = QApplication([])
    app.setFont(QFont("Segoe UI", 10))
    ex = ImageTrainerApp()
    ex.show()
    app.exec()
