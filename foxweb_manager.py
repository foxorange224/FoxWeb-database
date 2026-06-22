#!/usr/bin/env python3
import sys, json, os, base64, hashlib
from PIL import Image
from PyQt5 import QtWidgets, QtCore, QtGui

PASSWORD = "X9f2-K7wQ-M5pZ-V2tRt-XyZ99"
ITERATIONS = 2000
DATA_FILE = "data.json"
ICONS_DIR = "icons"
MDS_DIR = "mds"

sbox = [
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
]

inv_sbox = [0] * 256
for i in range(256):
    inv_sbox[sbox[i]] = i

rcon = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36]

def xor_bytes(a, b):
    return bytes(i ^ j for i, j in zip(a, b))

def sub_word(word):
    return bytes(sbox[b] for b in word)

def rot_word(word):
    return word[1:] + word[:1]

def key_expansion(key):
    nk = len(key) // 4
    nr = nk + 6
    w = []
    for i in range(nk):
        w.append(key[4*i:4*i+4])
    for i in range(nk, 4 * (nr + 1)):
        temp = w[i-1]
        if i % nk == 0:
            temp = xor_bytes(sub_word(rot_word(temp)), bytes([rcon[i//nk - 1], 0, 0, 0]))
        elif nk > 6 and i % nk == 4:
            temp = sub_word(temp)
        w.append(xor_bytes(w[i-nk], temp))
    return [bytearray(b) for b in w]

def add_round_key(state, rk):
    for i in range(4):
        for j in range(4):
            state[j][i] ^= rk[i][j]

def sub_bytes(state):
    for i in range(4):
        for j in range(4):
            state[i][j] = sbox[state[i][j]]

def inv_sub_bytes(state):
    for i in range(4):
        for j in range(4):
            state[i][j] = inv_sbox[state[i][j]]

def shift_rows(state):
    state[1][0], state[1][1], state[1][2], state[1][3] = state[1][1], state[1][2], state[1][3], state[1][0]
    state[2][0], state[2][1], state[2][2], state[2][3] = state[2][2], state[2][3], state[2][0], state[2][1]
    state[3][0], state[3][1], state[3][2], state[3][3] = state[3][3], state[3][0], state[3][1], state[3][2]

def inv_shift_rows(state):
    state[1][0], state[1][1], state[1][2], state[1][3] = state[1][3], state[1][0], state[1][1], state[1][2]
    state[2][0], state[2][1], state[2][2], state[2][3] = state[2][2], state[2][3], state[2][0], state[2][1]
    state[3][0], state[3][1], state[3][2], state[3][3] = state[3][1], state[3][2], state[3][3], state[3][0]

def xtime(a):
    r = (a << 1) & 0xff
    if a & 0x80:
        r ^= 0x1b
    return r

def mix_columns(state):
    for i in range(4):
        a = [state[j][i] for j in range(4)]
        state[0][i] = xtime(a[0]) ^ (xtime(a[1]) ^ a[1]) ^ a[2] ^ a[3]
        state[1][i] = a[0] ^ xtime(a[1]) ^ (xtime(a[2]) ^ a[2]) ^ a[3]
        state[2][i] = a[0] ^ a[1] ^ xtime(a[2]) ^ (xtime(a[3]) ^ a[3])
        state[3][i] = (xtime(a[0]) ^ a[0]) ^ a[1] ^ a[2] ^ xtime(a[3])

def inv_mix_columns(state):
    for i in range(4):
        a = [state[j][i] for j in range(4)]
        state[0][i] = mul(14, a[0]) ^ mul(11, a[1]) ^ mul(13, a[2]) ^ mul(9, a[3])
        state[1][i] = mul(9, a[0]) ^ mul(14, a[1]) ^ mul(11, a[2]) ^ mul(13, a[3])
        state[2][i] = mul(13, a[0]) ^ mul(9, a[1]) ^ mul(14, a[2]) ^ mul(11, a[3])
        state[3][i] = mul(11, a[0]) ^ mul(13, a[1]) ^ mul(9, a[2]) ^ mul(14, a[3])

def mul(a, b):
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        hi = a & 0x80
        a = (a << 1) & 0xff
        if hi:
            a ^= 0x1b
        b >>= 1
    return p

def bytes_to_state(block):
    s = [[0]*4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            s[j][i] = block[i*4 + j]
    return s

def state_to_bytes(state):
    b = bytearray(16)
    for i in range(4):
        for j in range(4):
            b[i*4 + j] = state[j][i]
    return bytes(b)

def aes_encrypt_block(pt, rk):
    s = bytes_to_state(pt)
    add_round_key(s, rk[0:4])
    for rnd in range(1, 14):
        sub_bytes(s); shift_rows(s); mix_columns(s)
        add_round_key(s, rk[rnd*4:(rnd+1)*4])
    sub_bytes(s); shift_rows(s)
    add_round_key(s, rk[56:60])
    return state_to_bytes(s)

def aes_decrypt_block(ct, rk):
    s = bytes_to_state(ct)
    add_round_key(s, rk[56:60])
    for rnd in range(13, 0, -1):
        inv_shift_rows(s); inv_sub_bytes(s)
        add_round_key(s, rk[rnd*4:(rnd+1)*4])
        inv_mix_columns(s)
    inv_shift_rows(s); inv_sub_bytes(s)
    add_round_key(s, rk[0:4])
    return state_to_bytes(s)

def pkcs7_pad(data):
    n = 16 - (len(data) % 16)
    return data + bytes([n] * n)

def pkcs7_unpad(data):
    return data[:-data[-1]]

def aes_cbc_encrypt(pt, key, iv):
    padded = pkcs7_pad(pt); rk = key_expansion(key); prev = iv
    result = bytearray()
    for i in range(0, len(padded), 16):
        b = padded[i:i+16]; x = xor_bytes(b, prev)
        e = aes_encrypt_block(x, rk); result.extend(e); prev = e
    return bytes(result)

def aes_cbc_decrypt(ct, key, iv):
    rk = key_expansion(key); prev = iv
    result = bytearray()
    for i in range(0, len(ct), 16):
        b = ct[i:i+16]; d = aes_decrypt_block(b, rk)
        x = xor_bytes(d, prev); result.extend(x); prev = b
    return pkcs7_unpad(bytes(result))

def derive_key(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, ITERATIONS, dklen=32)

def encrypt_enlace(enlace, password):
    salt = os.urandom(16); iv = os.urandom(16)
    key = derive_key(password, salt)
    ct = aes_cbc_encrypt(enlace.encode('utf-8'), key, iv)
    return base64.b64encode(salt + iv + ct).decode('ascii')

def decrypt_enlace(encrypted_b64, password):
    payload = base64.b64decode(encrypted_b64)
    salt, iv, ct = payload[:16], payload[16:32], payload[32:]
    key = derive_key(password, salt)
    return aes_cbc_decrypt(ct, key, iv).decode('utf-8')

def is_encrypted(val):
    if not val or val == '#': return False
    if val.startswith('http://') or val.startswith('https://'): return False
    return True

def icon_path(item_id):
    return os.path.join(ICONS_DIR, f'{item_id}.webp')

def md_path(item_id):
    return os.path.join(MDS_DIR, f'{item_id}.md')


class FoxWebManager(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.data = {}
        self.password = PASSWORD
        self.current_cat = None
        self.current_idx = None
        self.modified = False
        self.categories_order = ['programas', 'sistemas', 'juegos', 'apks', 'extras']
        self.build_ui()
        self.load_data()

    def build_ui(self):
        self.setWindowTitle('FoxWeb Database Manager')
        self.setGeometry(100, 100, 1150, 720)

        mw = QtWidgets.QWidget()
        self.setCentralWidget(mw)
        ml = QtWidgets.QHBoxLayout(mw)

        left = QtWidgets.QWidget()
        left.setMaximumWidth(350)
        ll = QtWidgets.QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(['Nombre', 'ID'])
        self.tree.setColumnWidth(0, 200)
        self.tree.itemClicked.connect(self.on_tree_click)
        ll.addWidget(self.tree, 1)

        right = QtWidgets.QWidget()
        rl = QtWidgets.QVBoxLayout(right)

        tabs = QtWidgets.QTabWidget()
        self.form_widget = QtWidgets.QWidget()
        fl = QtWidgets.QFormLayout(self.form_widget)

        self.name_input = QtWidgets.QLineEdit()
        self.name_input.textChanged.connect(self.mark_modified)
        self.info_input = QtWidgets.QTextEdit()
        self.info_input.setMaximumHeight(80)
        self.info_input.textChanged.connect(self.mark_modified)
        self.enlace_input = QtWidgets.QLineEdit()
        self.enlace_input.textChanged.connect(self.mark_modified)
        self.id_input = QtWidgets.QLineEdit()
        self.id_input.setReadOnly(True)
        self.badges_input = QtWidgets.QLineEdit()
        self.badges_input.setPlaceholderText('Ej: LIGERO, OPEN SOURCE, WINDOWS XP')
        self.badges_input.textChanged.connect(self.on_badges_changed)

        self.badges_warn = QtWidgets.QLabel('')
        self.badges_warn.setStyleSheet('color: #e67e22; font-size: 11px;')
        self.badges_warn.setWordWrap(True)

        badges_container = QtWidgets.QWidget()
        bcl = QtWidgets.QVBoxLayout(badges_container)
        bcl.setContentsMargins(0, 0, 0, 0)
        bcl.setSpacing(0)
        bcl.addWidget(self.badges_input)
        bcl.addWidget(self.badges_warn)

        fl.addRow('Nombre:', self.name_input)
        fl.addRow('Info:', self.info_input)
        fl.addRow('Enlace:', self.enlace_input)
        fl.addRow('ID:', self.id_input)
        fl.addRow('Badges:', badges_container)

        icon_tab = QtWidgets.QWidget()
        il = QtWidgets.QVBoxLayout(icon_tab)

        self.icon_preview = QtWidgets.QLabel('Sin icono')
        self.icon_preview.setFixedSize(180, 180)
        self.icon_preview.setAlignment(QtCore.Qt.AlignCenter)
        self.icon_preview.setStyleSheet('background: #1a1a1a; border: 1px solid #333; border-radius: 8px; color: #666;')
        self.icon_preview.setScaledContents(True)

        icon_btn_row = QtWidgets.QHBoxLayout()
        self.btn_change_icon = QtWidgets.QPushButton('Cambiar icono...')
        self.btn_change_icon.clicked.connect(self.on_change_icon)
        self.btn_remove_icon = QtWidgets.QPushButton('Quitar icono')
        self.btn_remove_icon.clicked.connect(self.on_remove_icon)
        self.btn_fix_icons = QtWidgets.QPushButton('Reparar todos')
        self.btn_fix_icons.setStyleSheet('background: #f39c12; color: #fff; padding: 8px 16px; border: none; border-radius: 4px;')
        self.btn_fix_icons.clicked.connect(self.on_fix_icons)

        icon_btn_row.addWidget(self.btn_change_icon)
        icon_btn_row.addWidget(self.btn_remove_icon)
        icon_btn_row.addWidget(self.btn_fix_icons)

        self.icon_info_label = QtWidgets.QLabel('Selecciona un elemento para gestionar su icono')
        self.icon_info_label.setStyleSheet('color: #888;')
        self.icon_info_label.setWordWrap(True)

        il.addWidget(self.icon_preview, 0, QtCore.Qt.AlignCenter)
        il.addLayout(icon_btn_row)
        il.addWidget(self.icon_info_label)
        il.addStretch()

        tabs.addTab(self.form_widget, 'Editar')
        tabs.addTab(icon_tab, 'Icono')

        md_tab = QtWidgets.QWidget()
        mml = QtWidgets.QVBoxLayout(md_tab)

        md_label = QtWidgets.QLabel('Información adicional (markdown)')
        md_label.setStyleSheet('color: #aaa; font-size: 12px;')

        self.md_editor = QtWidgets.QTextEdit()
        self.md_editor.setPlaceholderText('Contenido en markdown...\n\nSintaxis especial:\n[boton de descarga, color=#hex, icono=fa-icon, enlace=url, title="Texto"]')
        self.md_editor.textChanged.connect(self.mark_modified)

        md_btn_row = QtWidgets.QHBoxLayout()
        self.btn_md_save = QtWidgets.QPushButton('Guardar .md')
        self.btn_md_save.setStyleSheet('background: #3498db; color: #fff; padding: 8px 16px; border: none; border-radius: 4px;')
        self.btn_md_save.clicked.connect(self.on_md_save)
        self.btn_md_delete = QtWidgets.QPushButton('Eliminar .md')
        self.btn_md_delete.setStyleSheet('background: #e74c3c; color: #fff; padding: 8px 16px; border: none; border-radius: 4px;')
        self.btn_md_delete.clicked.connect(self.on_md_delete)

        self.md_status = QtWidgets.QLabel('')
        self.md_status.setStyleSheet('color: #888;')

        md_btn_row.addWidget(self.btn_md_save)
        md_btn_row.addWidget(self.btn_md_delete)
        md_btn_row.addStretch()
        md_btn_row.addWidget(self.md_status)

        mml.addWidget(md_label)
        mml.addWidget(self.md_editor, 1)
        mml.addLayout(md_btn_row)

        tabs.addTab(md_tab, 'Info adicional')

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton('+ Nuevo')
        self.btn_add.setStyleSheet('background: #27ae60; color: #fff; padding: 8px 16px; border: none; border-radius: 4px;')
        self.btn_add.clicked.connect(self.on_add)

        self.btn_delete = QtWidgets.QPushButton('Eliminar')
        self.btn_delete.setStyleSheet('background: #e74c3c; color: #fff; padding: 8px 16px; border: none; border-radius: 4px;')
        self.btn_delete.clicked.connect(self.on_delete)

        self.btn_move_up = QtWidgets.QPushButton('▲ Subir')
        self.btn_move_up.setStyleSheet('background: #555; color: #fff; padding: 8px 12px; border: none; border-radius: 4px;')
        self.btn_move_up.clicked.connect(self.on_move_up)

        self.btn_move_down = QtWidgets.QPushButton('▼ Bajar')
        self.btn_move_down.setStyleSheet('background: #555; color: #fff; padding: 8px 12px; border: none; border-radius: 4px;')
        self.btn_move_down.clicked.connect(self.on_move_down)

        self.btn_reorder = QtWidgets.QPushButton('Reordenar IDs')
        self.btn_reorder.setStyleSheet('background: #8e44ad; color: #fff; padding: 8px 12px; border: none; border-radius: 4px;')
        self.btn_reorder.clicked.connect(self.on_reorder)

        self.btn_save = QtWidgets.QPushButton('Guardar')
        self.btn_save.setStyleSheet('background: #3498db; color: #fff; padding: 8px 16px; border: none; border-radius: 4px; font-weight: bold;')
        self.btn_save.clicked.connect(self.on_save)

        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_delete)
        btn_row.addWidget(self.btn_move_up)
        btn_row.addWidget(self.btn_move_down)
        btn_row.addWidget(self.btn_reorder)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_save)

        rl.addWidget(tabs, 1)
        rl.addLayout(btn_row)
        ml.addWidget(left, 1)
        ml.addWidget(right, 2)

        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)

    def load_data(self):
        if not os.path.exists(DATA_FILE):
            QtWidgets.QMessageBox.critical(self, 'Error', f'No se encuentra {DATA_FILE}')
            sys.exit(1)
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        self.data = {}
        for cat in self.categories_order:
            if cat in raw:
                self.data[cat] = []
                for item in raw[cat]:
                    d = dict(item)
                    if is_encrypted(d.get('enlace', '')):
                        try:
                            d['enlace'] = decrypt_enlace(d['enlace'], self.password)
                        except Exception:
                            pass
                    self.data[cat].append(d)
        for cat in raw:
            if cat not in self.categories_order:
                self.data[cat] = []
                for item in raw[cat]:
                    d = dict(item)
                    if is_encrypted(d.get('enlace', '')):
                        try:
                            d['enlace'] = decrypt_enlace(d['enlace'], self.password)
                        except Exception:
                            pass
                    self.data[cat].append(d)
                self.categories_order.append(cat)
        self.refresh_tree()
        self.modified = False
        self.status_bar.showMessage(f'Cargado: {sum(len(v) for v in self.data.values())} elementos', 5000)

    def refresh_tree(self):
        self.tree.clear()
        for cat in self.categories_order:
            if cat not in self.data:
                continue
            ci = QtWidgets.QTreeWidgetItem([cat.capitalize(), f'{len(self.data[cat])}'])
            ci.setData(0, QtCore.Qt.UserRole, ('cat', cat))
            f = ci.font(0); f.setBold(True); ci.setFont(0, f)
            self.tree.addTopLevelItem(ci)
            for idx, item in enumerate(self.data[cat]):
                s = QtWidgets.QTreeWidgetItem([item.get('name', ''), item.get('id', '')])
                s.setData(0, QtCore.Qt.UserRole, ('item', cat, idx))
                ci.addChild(s)
        self.tree.expandAll()

    def on_tree_click(self, item, col):
        data = item.data(0, QtCore.Qt.UserRole)
        if not data:
            return
        if data[0] == 'cat':
            self.current_cat = data[1]; self.current_idx = None
            self.clear_form()
            return
        _, cat, idx = data
        self.current_cat = cat; self.current_idx = idx
        entry = self.data[cat][idx]
        self.name_input.setText(entry.get('name', ''))
        self.info_input.setPlainText(entry.get('info', ''))
        self.enlace_input.setText(entry.get('enlace', ''))
        self.id_input.setText(entry.get('id', ''))
        self.badges_input.setText(', '.join(entry.get('badges', [])))
        self.update_icon_preview(entry.get('id', ''))
        self.load_md_content(entry.get('id', ''))
        self.modified = False

    def clear_form(self):
        for w in [self.name_input, self.enlace_input, self.id_input, self.badges_input]:
            w.clear()
        self.info_input.clear()
        self.icon_preview.clear()
        self.icon_preview.setText('Sin icono')
        self.icon_info_label.setText('Selecciona un elemento para gestionar su icono')
        self.md_editor.clear()
        self.md_status.setText('')
        self.modified = False

    def mark_modified(self):
        self.modified = True

    def on_badges_changed(self):
        self.mark_modified()
        text = self.badges_input.text()
        tags = [t.strip() for t in text.split(',') if t.strip()]
        warnings = []
        over_3 = len(tags) > 3
        over_14 = [t for t in tags if len(t) > 14]
        if over_3:
            warnings.append('⚠ Solo se puede poner como máximo 3 etiquetas')
            warnings.append('Nota: No se pone tantos etiquetas para no desbordar el contenido')
        if over_14:
            warnings.append(f'⚠ {len(over_14)} etiqueta(s) superan los 14 caracteres')
        self.badges_warn.setText('\n'.join(warnings))
        self.badges_warn.setVisible(bool(warnings))

    def update_icon_preview(self, item_id):
        path = icon_path(item_id)
        if os.path.exists(path):
            try:
                from PIL import Image as PilImage
                pil_img = PilImage.open(path).convert('RGBA')
                data = pil_img.tobytes('raw', 'RGBA')
                qimg = QtGui.QImage(data, pil_img.width, pil_img.height, QtGui.QImage.Format_RGBA8888)
                pix = QtGui.QPixmap.fromImage(qimg)
                if not pix.isNull():
                    self.icon_preview.setPixmap(pix.scaled(180, 180, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
                    self.icon_preview.setText('')
                    self.icon_info_label.setText(f'Icono: {item_id}.webp ({pil_img.width}x{pil_img.height})')
                    return
            except Exception:
                pass
        self.icon_preview.clear()
        self.icon_preview.setText('Sin icono')
        self.icon_info_label.setText(f'No hay icono para {item_id}')

    def on_change_icon(self):
        if self.current_idx is None or not self.current_cat:
            QtWidgets.QMessageBox.warning(self, 'Aviso', 'Selecciona un elemento primero')
            return
        entry = self.data[self.current_cat][self.current_idx]
        item_id = entry.get('id', '')
        if not item_id:
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Seleccionar icono', '',
            'Imágenes (*.png *.jpg *.jpeg *.gif *.bmp *.webp)'
        )
        if not path:
            return
        try:
            img = Image.open(path).convert('RGBA')
            w, h = img.size
            if w > 180 or h > 180:
                ratio = min(180 / w, 180 / h)
                img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
            os.makedirs(ICONS_DIR, exist_ok=True)
            out = icon_path(item_id)
            img.save(out, 'WEBP', quality=85)
            self.update_icon_preview(item_id)
            self.status_bar.showMessage(f'Icono guardado: {out}', 3000)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error', f'No se pudo procesar la imagen:\n{e}')

    def on_remove_icon(self):
        if self.current_idx is None or not self.current_cat:
            return
        entry = self.data[self.current_cat][self.current_idx]
        item_id = entry.get('id', '')
        out = icon_path(item_id)
        if os.path.exists(out):
            os.remove(out)
        self.update_icon_preview(item_id)
        self.status_bar.showMessage('Icono eliminado', 3000)

    def on_fix_icons(self):
        from PIL import Image as PilImage
        if not os.path.isdir(ICONS_DIR):
            QtWidgets.QMessageBox.warning(self, 'Aviso', f'No existe el directorio {ICONS_DIR}')
            return
        files = sorted(os.listdir(ICONS_DIR))
        fixed = 0
        for f in files:
            path = os.path.join(ICONS_DIR, f)
            if not os.path.isfile(path):
                continue
            try:
                img = PilImage.open(path)
                w, h = img.size
                needs_resize = w > 180 or h > 180
                needs_convert = img.format != 'WEBP'
                if not needs_resize and not needs_convert:
                    continue
                if img.mode not in ('RGBA', 'LA'):
                    img = img.convert('RGBA')
                if needs_resize:
                    r = min(180 / w, 180 / h)
                    img = img.resize((int(w * r), int(h * r)), PilImage.LANCZOS)
                img.save(path, 'WEBP', quality=85)
                fixed += 1
            except Exception as e:
                pass
        self.status_bar.showMessage(f'Iconos reparados: {fixed}', 5000)
        if self.current_idx is not None and self.current_cat:
            entry = self.data[self.current_cat][self.current_idx]
            self.update_icon_preview(entry.get('id', ''))

    def load_md_content(self, item_id):
        path = md_path(item_id)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.md_editor.setPlainText(f.read())
                self.md_status.setText(f'{item_id}.md')
            except Exception as e:
                self.md_editor.clear()
                self.md_status.setText(f'Error: {e}')
        else:
            self.md_editor.clear()
            self.md_status.setText('No hay .md')

    def on_md_save(self):
        if self.current_idx is None or not self.current_cat:
            QtWidgets.QMessageBox.warning(self, 'Aviso', 'Selecciona un elemento primero')
            return
        entry = self.data[self.current_cat][self.current_idx]
        item_id = entry.get('id', '')
        if not item_id:
            return
        content = self.md_editor.toPlainText()
        os.makedirs(MDS_DIR, exist_ok=True)
        with open(md_path(item_id), 'w', encoding='utf-8') as f:
            f.write(content)
        self.md_status.setText(f'{item_id}.md guardado')
        self.status_bar.showMessage(f'MD guardado: {item_id}.md', 3000)

    def on_md_delete(self):
        if self.current_idx is None or not self.current_cat:
            return
        entry = self.data[self.current_cat][self.current_idx]
        item_id = entry.get('id', '')
        path = md_path(item_id)
        if os.path.exists(path):
            os.remove(path)
        self.md_editor.clear()
        self.md_status.setText('.md eliminado')
        self.status_bar.showMessage(f'MD eliminado: {item_id}.md', 3000)

    def on_move_up(self):
        if self.current_idx is None or not self.current_cat:
            return
        if self.current_idx == 0:
            return
        items = self.data[self.current_cat]
        items[self.current_idx], items[self.current_idx - 1] = items[self.current_idx - 1], items[self.current_idx]
        self.current_idx -= 1
        self.refresh_tree()
        self.select_tree_item(self.current_cat, self.current_idx)
        self.modified = True

    def on_move_down(self):
        if self.current_idx is None or not self.current_cat:
            return
        items = self.data[self.current_cat]
        if self.current_idx >= len(items) - 1:
            return
        items[self.current_idx], items[self.current_idx + 1] = items[self.current_idx + 1], items[self.current_idx]
        self.current_idx += 1
        self.refresh_tree()
        self.select_tree_item(self.current_cat, self.current_idx)
        self.modified = True

    def select_tree_item(self, cat, idx):
        for i in range(self.tree.topLevelItemCount()):
            ci = self.tree.topLevelItem(i)
            d = ci.data(0, QtCore.Qt.UserRole)
            if d and d[0] == 'cat' and d[1] == cat:
                child = ci.child(idx)
                if child:
                    self.tree.setCurrentItem(child)
                    self.on_tree_click(child, 0)
                break

    def on_reorder(self):
        confirm = QtWidgets.QMessageBox.question(self, 'Reordenar IDs',
            '¿Reasignar IDs secuenciales y renombrar iconos/.md?\n'
            'Los elementos se ordenarán por categoría e ID actual.',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if confirm != QtWidgets.QMessageBox.Yes:
            return

        flat = []
        for cat in self.categories_order:
            if cat not in self.data:
                continue
            for item in self.data[cat]:
                flat.append((cat, item))
        flat.sort(key=lambda x: (self.categories_order.index(x[0]), int(x[1].get('id', '0'))))

        mapping = {}
        for new_idx, (cat, item) in enumerate(flat, 1):
            old_id = item.get('id', '')
            new_id = f'{new_idx:06d}'
            mapping[old_id] = new_id
            item['id'] = new_id

        for old_id, new_id in mapping.items():
            if old_id == new_id:
                continue
            old_icon = icon_path(old_id)
            new_icon = icon_path(new_id)
            if os.path.exists(old_icon):
                os.rename(old_icon, new_icon)
            old_md = md_path(old_id)
            new_md = md_path(new_id)
            if os.path.exists(old_md):
                os.rename(old_md, new_md)

        self.current_idx = None
        self.current_cat = None
        self.clear_form()
        self.refresh_tree()
        self.modified = True
        self.status_bar.showMessage(f'IDs reordenados: {len(flat)} elementos', 5000)

    def on_add(self):
        if not self.current_cat:
            QtWidgets.QMessageBox.warning(self, 'Aviso', 'Selecciona una categoría primero')
            return
        max_id = 0
        for cat in self.data.values():
            for it in cat:
                try:
                    max_id = max(max_id, int(it.get('id', '0')))
                except ValueError:
                    pass
        new_id = f'{max_id + 1:06d}'
        self.data[self.current_cat].append({
            'name': 'Nuevo elemento', 'icon': '', 'info': '',
            'enlace': '#', 'badges': [], 'id': new_id
        })
        self.refresh_tree()
        self.status_bar.showMessage(f'Nuevo elemento creado (ID: {new_id})', 3000)
        self.modified = True

    def on_delete(self):
        if self.current_idx is None or not self.current_cat:
            QtWidgets.QMessageBox.warning(self, 'Aviso', 'Selecciona un elemento para eliminar')
            return
        entry = self.data[self.current_cat][self.current_idx]
        r = QtWidgets.QMessageBox.question(self, 'Confirmar',
            f'¿Eliminar "{entry.get("name")}"?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if r == QtWidgets.QMessageBox.Yes:
            item_id = entry.get('id', '')
            ip = icon_path(item_id)
            if os.path.exists(ip):
                os.remove(ip)
            del self.data[self.current_cat][self.current_idx]
            self.current_idx = None; self.clear_form()
            self.refresh_tree(); self.modified = True
            self.status_bar.showMessage('Elemento eliminado', 3000)

    def on_save(self):
        if self.current_idx is not None and self.current_cat:
            self.save_current_item()
        output = {}
        for cat in self.categories_order:
            if cat not in self.data:
                continue
            output[cat] = []
            for item in self.data[cat]:
                e = dict(item)
                enl = e.get('enlace', '')
                if enl and enl != '#' and not enl.startswith('http'):
                    try:
                        e['enlace'] = decrypt_enlace(enl, self.password)
                    except Exception:
                        pass
                if e.get('enlace', '') and e['enlace'] != '#':
                    e['enlace'] = encrypt_enlace(e['enlace'], self.password)
                if 'modal' in e:
                    del e['modal']
                output[cat].append(e)
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        self.modified = False
        self.status_bar.showMessage('Guardado correctamente', 3000)

    def save_current_item(self):
        if self.current_idx is None or not self.current_cat:
            return
        entry = self.data[self.current_cat][self.current_idx]
        entry['name'] = self.name_input.text()
        entry['info'] = self.info_input.toPlainText()
        raw = self.enlace_input.text()
        entry['enlace'] = raw if raw and raw != '#' else '#'
        entry['badges'] = [b.strip() for b in self.badges_input.text().split(',') if b.strip()]
        if 'modal' in entry:
            del entry['modal']
        self.refresh_tree()
        self.modified = False


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')
    w = FoxWebManager()
    w.show()
    sys.exit(app.exec_())
