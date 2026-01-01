from app import create_app, db
from app.models import User, Barang, Laporan, Kategori

app = create_app()
with app.app_context():
    db.create_all()
    if Kategori.query.count() == 0:
        print("--- Tabel Kategori kosong, mulai menyuntik data awal... ---")
        kategori_default = [
            Kategori(nama_kategori="Sembako"),           # Bakal otomatis dapet ID 1
            Kategori(nama_kategori="Makanan & Cemilan"), # Bakal otomatis dapet ID 2
            Kategori(nama_kategori="Minuman"),           # Bakal otomatis dapet ID 3
            Kategori(nama_kategori="Perawatan Tubuh"),   # Bakal otomatis dapet ID 4
            Kategori(nama_kategori="Perlengkapan Rumah") # Bakal otomatis dapet ID 5
        ]
        
        try:
            db.session.bulk_save_objects(kategori_default)
            db.session.commit()
            print("--- Kategori Awal Berhasil Disuntik (ID 1-5)! ---")
        except Exception as e:
            db.session.rollback()
            print(f"--- Gagal suntik kategori: {str(e)} ---")

    print("Ahmad Apriansyah Ganteng")

if __name__ == '__main__':
    app.run(debug=True)
