import os
from pytube import Playlist
import dropbox
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

# Dropbox API token
DROPBOX_ACCESS_TOKEN = ''
CHUNK_SIZE = 8 * 1024 * 1024  # 8MB chunks

def download_first_video(playlist_url):
    playlist = Playlist(playlist_url)
    first_video = playlist.videos[0]

    stream = first_video.streams.filter(progressive=True, file_extension='mp4').first()
    if stream:
        video_path = stream.download(output_path='videos', filename=first_video.title + '.mp4')
        print(f'Downloaded: {first_video.title}')
        return video_path
    return None

def upload_to_dropbox(file_path, dropbox_path, dbx):
    file_size = os.path.getsize(file_path)
    with open(file_path, 'rb') as f, tqdm(total=file_size, unit='B', unit_scale=True, desc=file_path) as pbar:
        if file_size <= CHUNK_SIZE:
            dbx.files_upload(f.read(), dropbox_path)
        else:
            upload_session_start_result = dbx.files_upload_session_start(f.read(CHUNK_SIZE))
            pbar.update(CHUNK_SIZE)
            cursor = dropbox.files.UploadSessionCursor(
                session_id=upload_session_start_result.session_id,
                offset=f.tell()
            )
            commit = dropbox.files.CommitInfo(path=dropbox_path)

            while f.tell() < file_size:
                if (file_size - f.tell()) <= CHUNK_SIZE:
                    dbx.files_upload_session_finish(f.read(CHUNK_SIZE), cursor, commit)
                    pbar.update(file_size - f.tell())
                else:
                    dbx.files_upload_session_append_v2(f.read(CHUNK_SIZE), cursor)
                    cursor.offset = f.tell()
                    pbar.update(CHUNK_SIZE)
    print(f'Uploaded: {file_path} to {dropbox_path}')

def main():
    playlist_url = 'https://www.youtube.com/playlist?list=PLn_sJONMDFW8oc2tG8_wmTMrhdwZscRdq'
    dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN, timeout=None)

    # Create a directory for downloaded videos
    if not os.path.exists('videos'):
        os.makedirs('videos')

    video_path = download_first_video(playlist_url)

    if video_path:
        # Specify the Dropbox folder
        folder_name = "Rev Francis Adelaja Are's Sermons"
        dropbox_path = f'/{folder_name}/' + os.path.basename(video_path)

        with ThreadPoolExecutor(max_workers=4) as executor:
            future = executor.submit(upload_to_dropbox, video_path, dropbox_path, dbx)
            future.result()

    print(f'First video downloaded and uploaded to Dropbox in folder "{folder_name}".')

if __name__ == '__main__':
    main()
