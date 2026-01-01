from app import app, db
from app.models import User

with app.app_context():
    # Cari user yang tadi kamu daftarkan (pilih salah satu: username atau email)
    user = User.query.filter_by(username='admin').first() 
    
    if user:
        user.role = 'admin' # Ubah jadi admin
        db.session.commit()
        print(f"Mantap! {user.username} sekarang sudah jadi ADMIN.")
    else:
        print("User tidak ditemukan, daftar dulu di web!")
        