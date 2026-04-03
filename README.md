# Video Box Manager (Armbian + mpv)

Ung dung web nhe de quan ly playlist video local va dieu khien phat loop tren box Armbian.

## Tinh nang MVP
- Quet video tu thu muc local tren box (mp4/mkv/mov/avi/webm/m4v)
- Duyet danh sach thu muc/file tren box ngay trong giao dien web
- Upload video tu may dang mo trinh duyet vao thu muc tren box
- Quan ly thu vien video
- Tao va sap xep playlist
- Dieu khien player: Start, Pause/Resume, Next, Stop
- Theo doi trang thai player va thong bao loi
- Khi playback loi: dung phat va bao loi

## Chay nhanh
1. Cai Python 3.10+ va mpv
2. Tao virtual env va cai thu vien:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

3. Chay app:

```bash
python run.py
```

4. Mo trinh duyet trong LAN:
- http://IP_BOX:8080

## API chinh
- GET /api/videos
- POST /api/videos/scan
- GET /api/playlist
- POST /api/playlist/add
- POST /api/playlist/reorder
- DELETE /api/playlist/{item_id}
- POST /api/player/start
- POST /api/player/pause
- POST /api/player/next
- POST /api/player/stop
- GET /api/player/status

## Deploy systemd tren box
Copy file `video-box-manager.service` vao:
- /etc/systemd/system/video-box-manager.service

Lenh kich hoat:

```bash
sudo systemctl daemon-reload
sudo systemctl enable video-box-manager
sudo systemctl start video-box-manager
sudo systemctl status video-box-manager
```

## Chay bang Docker
1. Tao thu muc du lieu:

```bash
mkdir -p data videos
```

2. Build va chay:

```bash
docker compose up -d --build
```

3. Truy cap giao dien:
- http://IP_BOX:8080

4. Khi quet video trong UI, nhap thu muc:
- /videos

Upload video tu may tinh:
1. Mo panel `Thu muc tren box va Upload`
2. Nhap duong dan (vi du `/videos`) va bam `Mo thu muc`
3. Chon file video tren may va bam `Upload vao thu muc dang mo`
4. Sang panel `Thu vien video` bam `Quet thu muc` de dong bo nhanh neu can

5. Xem log:

```bash
docker compose logs -f
```

Luu y:
- `data/app.db` la database duoc luu ben ngoai container.
- `videos/` la thu muc ban mount de app quet video local.
- Neu box dung X11 de hien thi video, compose da mount `/tmp/.X11-unix` va `/dev/dri`.
