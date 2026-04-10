# Video Box Manager (Armbian + mpv)

Ung dung web nhe de quan ly playlist video local va dieu khien phat loop tren box Armbian.

## Tinh nang MVP
- Quet video tu thu muc local tren box (mp4/mkv/mov/avi/webm/m4v)
- Them link YouTube/URL vao playlist va phat truc tiep bang mpv
- Duyet danh sach thu muc/file tren box ngay trong giao dien web
- Upload video tu may dang mo trinh duyet vao thu muc tren box
- Quan ly thu vien video
- Tao va sap xep playlist
- Dieu khien player: Start, Pause/Resume, Next, Stop
- Theo doi trang thai player va thong bao loi
- Khi playback loi: dung phat va bao loi

## Chay nhanh
1. Cai Python 3.10+ va mpv
	- Neu can phat YouTube, cai them `yt-dlp`
2. Tao virtual env va cai thu vien:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Tren Armbian/Debian:

```bash
sudo apt update
sudo apt install -y mpv yt-dlp
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
- POST /api/playlist/add-youtube
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

Sau khi app chay, vao giao dien web va su dung:
1. Panel `Thu muc tren box va Upload` de mo folder va upload video tu may tinh vao box.
2. Panel `Thu vien video` de quet folder (vi du `/videos`) va cap nhat danh sach video hien tai.

Luu y:
- App khong luu thu vien/playlist vao DB, danh sach video doc truc tiep tu thu muc tren box.
