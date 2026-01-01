from app import db
from datetime import datetime, timedelta
def waktu_wib():
    # Mengambil waktu UTC lalu ditambah 7 jam untuk WIB
    return datetime.utcnow() + timedelta(hours=7)

class Laporan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kode_barang = db.Column(db.String(20)) 
    nama_barang = db.Column(db.String(100))
    supplier = db.Column(db.String(100))
    jumlah = db.Column(db.Integer)
    status = db.Column(db.String(20)) 
    kategori_id = db.Column(db.Integer, db.ForeignKey('kategori.id'), nullable=False)
    # Pakai 'default=waktu_wib' (tanpa kurung tutup)
    tanggal = db.Column(db.DateTime, default=waktu_wib)

class Kategori(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_kategori = db.Column(db.String(50), nullable=False, unique=True)
    # Ini buat nampilin daftar barang di kategori tersebut (opsional tapi bagus)
    barangs = db.relationship('Barang', backref='kategori', lazy=True)

class Barang(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kode_barang = db.Column(db.String(20), unique=True) # ID 0101, 0201 dll
    nama_barang = db.Column(db.String(100))
    jenis_barang = db.Column(db.String(50)) # Bahan Baku, dll
    stok = db.Column(db.Integer)
    supplier = db.Column(db.String(100))
    kategori_id = db.Column(db.Integer, db.ForeignKey('kategori.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100))
    username = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20), default='user') # Nilainya: 'admin' atau 'user'

