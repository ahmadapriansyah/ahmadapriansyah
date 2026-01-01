
from pydoc import html
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, make_response
from app import db, mail
from app.models import Kategori, Laporan, User, Barang
from sqlalchemy import func
from flask_mail import Message  
from io import BytesIO
from xhtml2pdf import pisa

main = Blueprint('main', __name__)
# --- 1. SIGN UP (VERSI LENGKAP + WARNA) ---
@main.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        nama = request.form.get('nama')
        username = request.form.get('username').strip().lower()
        email = request.form.get('email').strip().lower()
        pw = request.form.get('password')

        # FIX LOGIKA: Biar nggak tabrakan, asalkan username 'admin', dia ADMIN.
        # Email nggak perlu dipaksa jadi 'admin' juga biar nggak ribet.
        if username == 'admin':
            role_baru = 'admin'
        else:
            role_baru = 'user'

        # 1. Cek apakah username sudah ada
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash("Username sudah terdaftar! Pakai nama lain, bro.", "danger")
            return redirect(url_for('main.sign_up'))

        # 2. FIX: Cek apakah email sudah ada
        email_exists = User.query.filter_by(email=email).first()
        if email_exists:
            flash("Email ini sudah dipake orang lain! Pakai email lain, sialan hehe.", "danger")
            return redirect(url_for('main.sign_up'))

        # Kalau lolos dua cek di atas, baru simpan ke DB
        baru = User(nama=nama, username=username, email=email, password=pw, role=role_baru)
        
        try:
            db.session.add(baru)
            db.session.commit()
            # Category 'success' = HIJAU
            flash(f"Berhasil! Kamu terdaftar sebagai {role_baru.upper()}", "success")
            return redirect(url_for('main.sign_in'))
        except Exception as e:
            db.session.rollback() 
            flash("Waduh, ada masalah teknis pas nyimpen data!", "danger")
            return redirect(url_for('main.sign_up'))

    return render_template('sign-up.html')

# --- 2. SIGN IN (VERSI LENGKAP + WARNA) ---
@main.route('/sign-in', methods=['GET', 'POST'])
def sign_in():
    if request.method == 'POST':
        username = request.form.get('username').strip().lower() # Pake lower biar match
        pw = request.form.get('password')
        
        user = User.query.filter_by(username=username, password=pw).first()

        if user:
            session.clear()
            
            # Tetep gue kasih auto-repair buat jaga-jaga kalau ada data lama yang error
            if user.username.lower() == 'admin' and user.role != 'admin':
                user.role = 'admin'
                db.session.commit()

            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            
            flash(f"Login berhasil sebagai {user.role.upper()}", "success")
            return redirect(url_for('main.index'))
        else:
            flash("Login Gagal! Username atau Password salah.", "danger")
            
    return render_template('sign-in.html')

# --- 3. DASHBOARD (SENSING ROLE + LOGIKA KESEHATAN GUDANG) ---
@main.route('/')
@main.route('/dashboard')
def index():
    if 'user_id' not in session:
        return redirect(url_for('main.sign_in'))
        
   
    data_barang = Barang.query.filter_by(is_active=True).all()
    total_stok = db.session.query(func.sum(Barang.stok)).scalar() or 0
    total_masuk = db.session.query(func.sum(Laporan.jumlah)).filter(Laporan.status == "Masuk").scalar() or 0
    total_keluar = db.session.query(func.sum(Laporan.jumlah)).filter(Laporan.status == "Keluar").scalar() or 0
    kapasitas = round((total_stok / 1000) * 100, 1)


    stok_aman = Barang.query.filter(Barang.stok > 10).count()
    stok_menipis = Barang.query.filter(Barang.stok <= 10, Barang.stok > 0).count()
    stok_habis = Barang.query.filter(Barang.stok == 0).count()
    barang_kritis = Barang.query.filter(Barang.stok <= 5).all()
    
    return render_template('dashboard.html', 
                           data=data_barang, 
                           total_stok=total_stok,
                           total_masuk=total_masuk, 
                           total_keluar=total_keluar,
                           kapasitas=kapasitas,
                           aman=stok_aman,
                           menipis=stok_menipis,
                           habis=stok_habis,
                           kritis=barang_kritis)
# --- 4. PROTEKSI HALAMAN (MASUK) ---
@main.route('/masuk', methods=['GET', 'POST'])
def masuk():
    if session.get('role') != 'admin':
        flash("Akses ditolak! Kamu bukan admin.")
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        nama = request.form.get('nama_barang')
        jumlah = request.form.get('stok')
        vendor = request.form.get('supplier')
        kat_id = request.form.get('kategori_id')

        if not nama or not jumlah:
            flash("Data tidak lengkap!")
            return redirect(url_for('main.masuk'))

        try:
            barang = Barang.query.filter_by(nama_barang=nama).first()
            
            if barang:
                barang.stok += int(jumlah)
            else:
                barang = Barang(nama_barang=nama, 
                                stok=int(jumlah), 
                                supplier=vendor,
                                kategori_id=int(kat_id))
                db.session.add(barang)
            
            # 1. FLUSH buat dapet ID (Biar nggak None)
            db.session.flush() 

            # 2. RAKIT KODE SAKTI (01-06-01)
            kategori = Kategori.query.get(kat_id)
            # Ambil kode kategori, kalo gak ada pake ID kategori di-zfill
            k_kat = kategori.kode_kategori if (hasattr(kategori, 'kode_kategori') and kategori.kode_kategori) else str(kat_id).zfill(2)
            k_brg = str(barang.id).zfill(2)
            urutan = str(Laporan.query.filter_by(nama_barang=nama).count() + 1).zfill(2)
            
            kode_final = f"{k_kat}-{k_brg}-{urutan}"

            # 3. Simpan ke Laporan (Pake kode_final)
            laporan_baru = Laporan(
                kode_barang=kode_final, # Sekarang isinya jadi 01-06-01
                nama_barang=nama, 
                jumlah=int(jumlah), 
                status="Masuk", 
                supplier=vendor,
                kategori_id=int(kat_id)
            )
            db.session.add(laporan_baru)
            db.session.commit()
            
            flash(f"Berhasil! {nama} masuk dengan kode {kode_final}", "success")
            return redirect(url_for('main.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}")
            return redirect(url_for('main.masuk'))
            
    daftar_kategori = Kategori.query.all()
    return render_template('masuk.html', kategori=daftar_kategori)

@main.route('/tambah-kategori', methods=['POST'])
def tambah_kategori():
    nama_baru = request.form.get('nama_baru')
    if nama_baru:
        existing = Kategori.query.filter_by(nama_kategori=nama_baru).first()
        if not existing:
            kat = Kategori(nama_kategori=nama_baru)
            db.session.add(kat)
            db.session.commit()
            flash(f"Kategori '{nama_baru}' berhasil dibuat!", "success")
        else:
            flash("Kategori itu udah ada, Mad!", "warning")
    return redirect(url_for('main.masuk'))

@main.route('/keluar', methods=['GET', 'POST'])
def keluar():
    if session.get('role') != 'admin':
        flash("Akses ditolak! Kamu bukan admin.")
        return redirect(url_for('main.index'))
    
    
    data_barang = Barang.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        # Ambil nama barang dan jumlah yang mau dikeluarin
        nama = request.form.get('nama_barang')
        jumlah_input = request.form.get('stok')
        barang = Barang.query.filter_by(nama_barang=nama).first()

        if barang and barang.stok >= int(jumlah_input):
            # 1. Kurangi stok barang
            barang.stok -= int(jumlah_input)
            kategori = Kategori.query.get(barang.kategori_id)
            k_kat = kategori.kode_kategori if (hasattr(kategori, 'kode_kategori') and kategori.kode_kategori) else str(barang.kategori_id).zfill(2)
            k_brg = str(barang.id).zfill(2)
            urutan = str(Laporan.query.filter_by(nama_barang=nama).count() + 1).zfill(2)
            kode_final = f"{k_kat}-{k_brg}-{urutan}"
            # 2. Catat ke tabel Laporan (Status: Keluar)
            laporan_keluar = Laporan(
            kode_barang=kode_final, 
            nama_barang=nama, 
            jumlah=int(jumlah_input), 
            status="Keluar", 
            supplier=barang.supplier,
            kategori_id=barang.kategori_id)

            db.session.add(laporan_keluar)
            db.session.commit()
            if barang.stok <= 5:
                email_status = kirim_email_peringatan(barang.nama_barang, barang.stok)
                
                if email_status:
                    flash(f"Berhasil! {jumlah_input} unit keluar. PERINGATAN: Stok kritis ({barang.stok}), email notif terkirim!", "warning")
                else:
                    flash(f"Berhasil! {jumlah_input} unit keluar. Stok kritis ({barang.stok}), tapi gagal kirim email.", "warning")
            else:
                # Kalau stok masih banyak (di atas 5)
                flash(f"Berhasil mengeluarkan {jumlah_input} unit {nama}!", "success")
            
            return redirect(url_for('main.index'))
            
        else:
            flash("Gagal! Stok tidak cukup atau barang tidak ditemukan.", "danger")
            return redirect(url_for('main.keluar'))

    return render_template('keluar.html', data=data_barang)

def kirim_email_peringatan(nama_barang, sisa_stok):
    try:
        msg = Message(
            subject=f"⚠️ WASPADA: Stok {nama_barang} Menipis!",
            sender="Sistemgudang@gmail.com", # Email Robot
            recipients=["ahmad240101034@gmail.com"] # Email Lo buat nerima
        )
        msg.body = (f"Halo Bos,\n\n"
                    f"Barang '{nama_barang}' baru saja dikeluarkan.\n"
                    f"Sisa stok saat ini tinggal {sisa_stok} unit.\n\n"
                    f"Segera hubungi supplier untuk restock!\n\n"
                    f"Salam,\nKelola Gudang")
        mail.send(msg)
        print("--- EMAIL BERHASIL TERKIRIM! ---")
        return True
    except Exception as e:
    # Ganti 'print' ini biar keliatan di terminal error aslinya apa
     print(f"--- ERROR GAGAL KIRIM EMAIL: {str(e)} ---")
    return False

@main.route('/tables')
def tables():
    data = Barang.query.filter_by(is_active=True).all()
    return render_template('tables.html', data=data)

@main.route('/arsipkan-barang/<int:id>')
def arsipkan_barang(id):
    if session.get('role') != 'admin':
        flash("Hanya admin yang bisa mengarsipkan barang!")
        return redirect(url_for('main.index'))

    barang = Barang.query.get_or_404(id)
    barang.is_active = False # Set jadi non-aktif
    db.session.commit()
    
    flash(f"Barang '{barang.nama_barang}' berhasil diarsipkan!", "warning")
    return redirect(url_for('main.tables'))

@main.route('/restore-barang/<int:id>')
def restore_barang(id):
    # Proteksi: Cuma admin yang boleh balikin barang
    if session.get('role') != 'admin':
        flash("Hanya admin yang bisa memulihkan barang!", "danger")
        return redirect(url_for('main.index'))

    # Cari barangnya di database
    barang = Barang.query.get_or_404(id)
    
    # Ubah statusnya jadi True (Aktif lagi)
    barang.is_active = True 
    db.session.commit()
    
    flash(f"MANTAP! Barang '{barang.nama_barang}' sudah aktif lagi!", "success")
    # Balikin ke halaman tables atau arsip terserah lo, gue saranin ke tables
    return redirect(url_for('main.tables'))

@main.route('/arsip')
def arsip_list():
    # Ambil yang is_active-nya False
    data_arsip = Barang.query.filter_by(is_active=False).all()
    return render_template('arsip.html', data=data_arsip)

# --- FUNGSI 1: CUMA BUAT TAMPILIN HALAMAN TABEL DI BROWSER ---
@main.route('/laporan')
def laporan():
    data = Laporan.query.order_by(Laporan.tanggal.desc()).all()
    # Lo cuma perlu render laporan.html di sini
    return render_template('laporan.html', data=data)


@main.route('/download_laporan')
def download_laporan():
    # 1. Ambil data
    data_laporan = Laporan.query.order_by(Laporan.tanggal.desc()).all()
    
    # 2. Render template khusus PDF (pake file pdf_template.html yang gue kasih tadi)
    html = render_template('pdf_template.html', data=data_laporan)
    
    # 3. Proses jadi PDF
    result = BytesIO()
    pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    # 4. Kirim filenya supaya otomatis ke-download
    response = make_response(result.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=Laporan_Gudang_Ahmad.pdf'
    return response
@main.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.sign_in'))

